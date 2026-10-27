import argparse
import json
import sys
from pathlib import Path

# Đưa thư mục src vào sys.path để import module dùng chung
CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR.parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Phải configure() TRƯỚC khi import các stage dùng TensorFlow/PyTorch.
from log_config import configure, get_logger

configure()
logger = get_logger(__name__)

from env_config import get_env

# Import PyTorch before TensorFlow-dependent stages.
from proposed.resnet_inference import ResNetClassifier
from proposed.diversity_spatial_sampler import DiversitySpatialSampler
from proposed.compressed_color_sampler import CompressedColorSampler
from proposed.coarse_mobilenet_filter import CoarseMobileNetFilter
from proposed.dual_branch_evaluator import DualBranchEvaluator
from proposed.streaming_cascade import run_cascade


def main():
    parser = argparse.ArgumentParser(
        description="PBL6 Proposed Sensitive Video Moderation Pipeline (Cascade 4 Stages)"
    )
    parser.add_argument("--video", type=str, required=True, help="Đường dẫn đến file video cần phân tích")
    parser.add_argument(
        "--out_dir",
        type=str,
        default=get_env("PROPOSED_OUT_DIR", "ProposedLog", resolve=True),
        help="Thư mục lưu log và kết quả phán quyết"
    )
    parser.add_argument(
        "--mobilenet_model",
        type=str,
        default=get_env("MOBILENET_MODEL", "models/mobilenetv3_small_adult_normal.keras", resolve=True),
        help="Đường dẫn mô hình MobileNetV3-Small (.keras)"
    )
    parser.add_argument(
        "--resnet_model",
        type=str,
        default=get_env("PROPOSED_MODEL", "models/resnet50_adult_normal_fcn_layer4_classifier.pth", resolve=True),
        help="Đường dẫn mô hình ResNet50 FCN (.pth)"
    )
    parser.add_argument(
        "--delta_t",
        type=float,
        default=0.5,
        help="Khoảng cách thời gian tối đa giữa các frame lấy mẫu cơ sở (mặc định: 0.5s)"
    )
    parser.add_argument(
        "--z_threshold",
        type=float,
        default=3.0,
        help="Ngưỡng Z-score phát hiện đột biến flash nhấp nháy (mặc định: 3.0)"
    )
    parser.add_argument(
        "--rejection_threshold",
        type=float,
        default=0.35,
        help="Ngưỡng loại bỏ sớm của MobileNetV3-Small ở Bước 2 (mặc định: 0.35)"
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=32,
        help="Số mẫu Stage 1 tích lũy trước khi chạy MobileNet (mặc định: 32)"
    )
    parser.add_argument(
        "--early_stop",
        action="store_true",
        default=True,
        help="Dừng sớm ngay khi phát hiện mốc vi phạm Adult đầu tiên (mặc định: True)"
    )
    parser.add_argument(
        "--no_early_stop",
        dest="early_stop",
        action="store_false",
        help="Không dừng sớm, quét toàn bộ video kể cả khi đã phát hiện Adult"
    )
    parser.add_argument(
        "--save_intermediate",
        action="store_true",
        help="Lưu kết quả JSON và frames trung gian ở từng giai đoạn"
    )
    args = parser.parse_args()

    video_path = Path(args.video).resolve()
    base_out = Path(args.out_dir) / video_path.stem

    # Load models before timing video processing.
    logger.info("Khởi tạo các mô hình và bộ lọc cho Pipeline đề xuất...")
    stage1_sampler = CompressedColorSampler(
        delta_t=args.delta_t,
        z_threshold=args.z_threshold,
        window_size=15
    )
    stage2_filter = CoarseMobileNetFilter(
        model_path=args.mobilenet_model,
        batch_size=args.batch_size,
        rejection_threshold=args.rejection_threshold
    )
    resnet = ResNetClassifier(model_path=args.resnet_model)
    diversity_sampler = DiversitySpatialSampler(
        sampling_fps=10.0
    )
    evaluator = DualBranchEvaluator()

    # Warm up model kernels before timing.
    logger.info("Thực hiện Warm-up pass (MobileNetV3 & ResNet-50 FCN)...")
    stage2_filter.warmup()
    resnet.warmup()
    logger.info("Hoàn tất Warm-up. Hệ thống sẵn sàng đo đạc thời gian video.")

    logger.info(f"BẮT ĐẦU PIPELINE ĐỀ XUẤT (PROPOSED PIPELINE): {video_path.name}")

    def log_anchor(anchor_eval, evaluated_count):
        prefix = (
            f"[Anchor {evaluated_count:02d}] {anchor_eval['anchor_frame_index']} "
            f"({anchor_eval['anchor_time_sec']:.2f}s) | "
        )
        if anchor_eval["decision"] == "ADULT":
            logger.info(
                prefix
                + f"==> VI PHẠM ADULT ({anchor_eval['violation_type']}) | "
                + f"p_mobile: {anchor_eval['p_mobile']:.3f}, "
                + f"p_resnet: {anchor_eval['p_resnet_anchor']:.3f}, "
                + f"Z_flash: {anchor_eval['z_flash']:.2f}"
            )
            if args.early_stop:
                logger.info("Kích hoạt --early_stop: Dừng sớm ngay khi phát hiện vi phạm Adult.")
        else:
            logger.debug(
                prefix
                + f"NORMAL | p_mobile: {anchor_eval['p_mobile']:.3f}, "
                + f"p_resnet: {anchor_eval['p_resnet_anchor']:.3f}"
            )

    result = run_cascade(
        video_path,
        stage1_sampler=stage1_sampler,
        stage2_filter=stage2_filter,
        resnet_classifier=resnet,
        diversity_sampler=diversity_sampler,
        evaluator=evaluator,
        early_stop=args.early_stop,
        batch_size=args.batch_size,
        stage1_output_dir=base_out / "01_stage1_frames" if args.save_intermediate else None,
        stage2_json_path=base_out / "02_stage2_coarse.json" if args.save_intermediate else None,
        final_json_path=base_out / "08_final_decision.json",
        on_anchor_evaluated=log_anchor,
    )

    timings = result["timings"]
    stats = result["stats"]
    final_result = result["final_summary"]

    logger.info(
        f">> Thời gian từng giai đoạn: Stage 1 (decode + HSV) {timings['stage1']:.2f}s | "
        f"Stage 2 (MobileNet) {timings['stage2']:.2f}s | "
        f"Stage 3 (Diversity) {timings['stage3']:.2f}s | "
        f"Stage 4 (ResNet + hai nhánh) {timings['stage4']:.2f}s"
    )

    if stats["stop_reason"] == "no_stage1_samples":
        logger.warning("Không trích xuất được frame nào từ video. Kết luận: NORMAL.")
    elif stats["stop_reason"] == "all_candidates_rejected_by_mobilenet":
        logger.info("TẤT CẢ CÁC FRAMES ĐÃ BỊ LOẠI BỎ SỚM TẠI STAGE 2 (p_mobile < 0.35) -> VIDEO AN TOÀN (NORMAL).")
    elif stats["stop_reason"] == "adult_detected":
        decoded = stats["decoded_frames"]
        total_frames = result["video_info"]["total_frames"]
        pct = (decoded / total_frames * 100) if total_frames else 100.0
        logger.info(
            f"DỪNG SỚM: chỉ cần decode {decoded}/{total_frames} frames ({pct:.1f}%) "
            f"để ra phán quyết ADULT."
        )

    if args.save_intermediate and final_result is not None:
        with open(base_out / "04_final_decision.json", "w", encoding="utf-8") as f:
            json.dump(final_result, f, indent=2, ensure_ascii=False)

    total_elapsed = timings["total"]
    logger.info(
        f"KẾT LUẬN TOÀN BỘ VIDEO: {final_result['final_decision']} "
        f"(Tổng thời gian xử lý: {total_elapsed:.2f}s | "
        f"Số vùng vi phạm: {final_result['total_adult_regions']})"
    )


if __name__ == "__main__":
    main()
