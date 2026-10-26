"""
Pipeline Proposed 4 giai đoạn chạy streaming (dùng chung cho CLI và benchmark).

Khác với bản cũ (decode hết video -> suy luận hết -> mới đánh giá anchor), bản
này chồng 4 giai đoạn lên nhau theo từng frame:

    decode 1 frame
      -> Stage 1: histogram HSV / Bhattacharyya / Z-score, chọn mẫu
      -> khi đủ ``batch_size`` mẫu: Stage 2 MobileNet (loại sớm / gom anchor)
      -> anchor kế tiếp đã rõ: Stage 3 (D* trên [t_i, t_i+1)) + Stage 4 ResNet
      -> nếu anchor đó là ADULT và ``early_stop``: dừng luôn vòng decode

Nhờ vậy video Adult dừng sớm ngay khi phát hiện vi phạm, thay vì vẫn phải
decode 100% video và chạy MobileNet trên toàn bộ mẫu trước.

Điểm quan trọng về độ chính xác: một anchor chỉ được đánh giá khi đã biết
anchor kế tiếp, nên tập D* luôn là [t_i, t_i+1) đúng như bản cũ -> kết quả
từng anchor (p_resnet, branch, decision) không đổi. Đánh đổi: nếu video chỉ có
một anchor thì phải quét hết video mới phán quyết được anchor đó.
"""

import json
import logging
import math
import time
from pathlib import Path

import cv2

logger = logging.getLogger(__name__)


def run_cascade(
    video_path,
    *,
    stage1_sampler,
    stage2_filter,
    resnet_classifier,
    diversity_sampler,
    evaluator,
    early_stop=True,
    batch_size=32,
    stage1_output_dir=None,
    stage2_json_path=None,
    final_json_path=None,
    on_anchor_evaluated=None,
):
    """
    Chạy toàn bộ cascade 4 giai đoạn trên một video theo kiểu streaming.

    Tham số
    -------
    stage1_sampler, stage2_filter, resnet_classifier, diversity_sampler, evaluator:
        Các stage đã được khởi tạo sẵn (như CLI/benchmark vẫn làm).
    early_stop:
        True = dừng ngay khi anchor đầu tiên là ADULT (mặc định của CLI).
    batch_size:
        Số mẫu Stage 1 tích lũy trước khi gọi MobileNet (thông số --batch_size).
    stage1_output_dir, stage2_json_path, final_json_path:
        Đường dẫn debug/output; ``None`` thì không ghi.
    on_anchor_evaluated:
        Callback ``fn(anchor_eval, evaluated_count)`` gọi sau mỗi anchor.

    Trả về dict gồm: video_info, samples, anchors, anchor_evaluations,
    final_summary, stats, timings (stage1/2/3/4/total).
    """
    video_path = Path(video_path).resolve()
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Không mở được video: {video_path}")

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    total_hint = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if fps <= 0:
        fps = 25.0

    if stage1_output_dir:
        Path(stage1_output_dir).mkdir(parents=True, exist_ok=True)

    stage1_sampler.start_scan(fps)

    samples = []          # mọi sample đã quét (sau khi score thì không còn frame_data)
    scored = []           # các sample thật sự đã qua MobileNet
    pending = []          # lô chờ suy luận (vẫn giữ frame_data)
    anchors = []          # Anchor Set A (giữ frame_data tới khi được đánh giá)
    anchor_evaluations = []
    next_anchor_to_eval = 0

    timings = {"stage1": 0.0, "stage2": 0.0, "stage3": 0.0, "stage4": 0.0, "total": 0.0}
    stats = {
        "decoded_frames": 0,
        "stage1_selected": 0,
        "stage2_candidates_in": 0,
        "anchors_discovered": 0,
        "stage3_diverse_frames": 0,
        "stage4_resnet_frames": 0,
        "stop_reason": "end_of_video",
    }

    stopped = False
    cap_stage3 = None
    t_start = time.perf_counter()

    def _end_boundary():
        """Ranh giới kết thúc video theo số frame đã decode (giống bản cũ)."""
        return stats["decoded_frames"] / fps if fps > 0 else 0.0

    def _evaluate_ready(at_end):
        """Đánh giá các anchor đã có đủ dữ liệu (đã biết anchor kế tiếp)."""
        nonlocal next_anchor_to_eval, stopped, cap_stage3

        while next_anchor_to_eval < len(anchors) and not stopped:
            idx = next_anchor_to_eval
            anchor = anchors[idx]

            if idx + 1 < len(anchors):
                boundary = anchors[idx + 1]["time_sec"]
            elif at_end:
                boundary = _end_boundary()
            else:
                # Chưa biết anchor kế tiếp: chờ để giữ nguyên tập D* [t_i, t_i+1)
                break

            t_0 = anchor["time_sec"]
            segment_duration = max(0.0, boundary - t_0)
            target_num_frames = min(32, 3 + math.floor(segment_duration))

            if cap_stage3 is None:
                cap_stage3 = cv2.VideoCapture(str(video_path))

            t0 = time.perf_counter()
            d_star = diversity_sampler.extract_diverse_frames(
                cap=cap_stage3,
                fps=fps,
                anchor=anchor,
                video_duration_sec=_end_boundary(),
                next_anchor_time_sec=boundary,
                target_num_frames=target_num_frames,
            )
            timings["stage3"] += time.perf_counter() - t0
            stats["stage3_diverse_frames"] += len(d_star)

            t0 = time.perf_counter()
            anchor_eval = evaluator.evaluate_anchor(
                anchor=anchor,
                d_star_frames=d_star,
                resnet_classifier=resnet_classifier,
            )
            timings["stage4"] += time.perf_counter() - t0
            stats["stage4_resnet_frames"] += len(d_star)

            anchor_evaluations.append(anchor_eval)
            anchor.pop("frame_data", None)   # trả RAM ngay khi xong
            next_anchor_to_eval = idx + 1

            if on_anchor_evaluated:
                on_anchor_evaluated(anchor_eval, len(anchor_evaluations))

            if anchor_eval["decision"] == "ADULT" and early_stop:
                stopped = True
                stats["stop_reason"] = "adult_detected"

    def _flush_pending():
        """Chạy MobileNet trên lô mẫu đang chờ rồi đánh giá các anchor đủ điều kiện."""
        if not pending:
            return

        chunk = pending[:]
        pending.clear()

        t0 = time.perf_counter()
        new_anchors = stage2_filter.score_samples(chunk)
        timings["stage2"] += time.perf_counter() - t0

        stats["stage2_candidates_in"] += len(chunk)
        scored.extend(chunk)

        anchor_ids = {id(a) for a in new_anchors}
        for sample in chunk:
            if id(sample) not in anchor_ids:
                sample.pop("frame_data", None)   # trả RAM ngay sau khi suy luận

        anchors.extend(new_anchors)
        stats["anchors_discovered"] = len(anchors)

        _evaluate_ready(at_end=False)

    # ------------------------------------------------------------------
    # Vòng decode: đọc tới đâu thì xử lý tới đó, dừng ngay khi có phán quyết
    # ------------------------------------------------------------------
    while True:
        t0 = time.perf_counter()
        ok, frame = cap.read()
        timings["stage1"] += time.perf_counter() - t0
        if not ok or frame is None:
            break
        stats["decoded_frames"] += 1

        image_path = None
        if stage1_output_dir:
            idx = stage1_sampler.frame_index
            image_path = str(
                Path(stage1_output_dir) / f"frame_{idx:06d}_{idx / fps:.2f}s.jpg"
            )

        t0 = time.perf_counter()
        sample = stage1_sampler.feed(frame, image_path=image_path)
        timings["stage1"] += time.perf_counter() - t0

        if sample is not None:
            samples.append(sample)
            pending.append(sample)

        if len(pending) >= batch_size:
            _flush_pending()
            if stopped:
                break

    if not stopped:
        # Quét hết video: chốt nốt lô cuối rồi đánh giá anchor còn lại
        # (anchor cuối dùng thời lượng video làm ranh giới, đúng như bản cũ).
        _flush_pending()
        _evaluate_ready(at_end=True)

    cap.release()
    if cap_stage3 is not None:
        cap_stage3.release()
    diversity_sampler.clear_cache()

    timings["total"] = time.perf_counter() - t_start

    # ------------------------------------------------------------------
    # Tổng hợp kết quả
    # ------------------------------------------------------------------
    scan_complete = not stopped
    decoded = stats["decoded_frames"]
    # Quét hết video thì dùng số frame đọc được (đúng như bản cũ); dừng sớm thì
    # giữ số frame khai báo của header. Trường hợp không decode được frame nào
    # vẫn lấy total_hint để metadata không bị 0 như bản cũ.
    total_frames = decoded if (scan_complete and decoded) else max(total_hint, decoded)

    # Trả RAM: mọi frame còn sót trong các sample chưa score (dừng sớm) đều gỡ.
    for sample in samples:
        sample.pop("frame_data", None)

    shots = stage1_sampler.finish_scan(samples, total_frames=total_frames)
    video_info = stage1_sampler.scan_stats(
        video_path=video_path,
        total_frames=total_frames,
        decoded_frames=decoded,
        scan_complete=scan_complete,
        shots=shots,
    )

    if stats["stop_reason"] == "end_of_video":
        if not samples:
            stats["stop_reason"] = "no_stage1_samples"
        elif stats["anchors_discovered"] == 0:
            stats["stop_reason"] = "all_candidates_rejected_by_mobilenet"

    if stage2_json_path:
        stage2_json_path = Path(stage2_json_path)
        stage2_json_path.parent.mkdir(parents=True, exist_ok=True)
        records = stage2_filter.build_stage2_records(scored)
        with open(stage2_json_path, "w", encoding="utf-8") as f:
            json.dump({
                "total_candidates": len(scored),
                "rejected_count": len(scored) - len(anchors),
                "anchor_count": len(anchors),
                "rejection_threshold": stage2_filter.rejection_threshold,
                "results": records,
            }, f, indent=2, ensure_ascii=False)

    final_summary = None
    if final_json_path:
        final_summary = evaluator.evaluate_video(
            video_path=video_path,
            anchor_evaluations=anchor_evaluations,
            video_info=video_info,
            output_json_path=final_json_path,
            save_to_disk=True,
        )

    stats["stage1_selected"] = len(samples)

    logger.debug(
        "Cascade streaming: decoded=%s/%s | stage1=%s | anchors=%s | evaluated=%s | stop=%s",
        decoded, total_frames, len(samples), len(anchors),
        len(anchor_evaluations), stats["stop_reason"],
    )

    return {
        "video_info": video_info,
        "samples": samples,
        "anchors": anchors,
        "anchor_evaluations": anchor_evaluations,
        "final_summary": final_summary,
        "stats": stats,
        "timings": timings,
    }
