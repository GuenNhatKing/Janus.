import cv2
import numpy as np


class DiversitySpatialSampler:
    """Select visually diverse frames from an anchor's forward interval."""

    def __init__(self, time_window_radius=1.0, sampling_fps=10.0, target_num_frames=1):
        self.time_window_radius = time_window_radius
        self.sampling_fps = sampling_fps
        self.target_num_frames = target_num_frames
        # Cache decoded frames and vectors so overlapping windows reuse data.
        self._frame_cache = {}
        self._vector_cache = {}
        self._current_cap_pos = -1

    def clear_cache(self):
        """Giải phóng bộ đệm RAM khi chuyển sang video mới."""
        self._frame_cache.clear()
        self._vector_cache.clear()
        self._current_cap_pos = -1

    def _frame_to_unit_vector(self, frame_bgr):
        """
        Chuyển frame BGR sang ảnh xám 32x32, làm phẳng thành vector 1024 chiều,
        chuẩn hóa L2 thành vector đơn vị: ||v||_2 = 1.
        """
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        small = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA)
        vec = small.astype(np.float32).flatten()
        norm = float(np.linalg.norm(vec))
        if norm > 1e-8:
            vec = vec / norm
        else:
            vec = np.zeros_like(vec)
        return vec

    def extract_diverse_frames(
        self,
        cap,
        fps,
        anchor,
        video_duration_sec,
        next_anchor_time_sec=None,
        target_num_frames=None,
    ):
        """
        Lấy frame trong [t0, t1), bao gồm anchor và không lấy frame ngoài
        khoảng này.
        """
        t_0 = anchor["time_sec"]
        t_start = max(0.0, t_0)
        t_end = min(
            video_duration_sec,
            next_anchor_time_sec if next_anchor_time_sec is not None else video_duration_sec,
        )
        if t_end < t_start:
            t_start = t_end

        dense_interval = 1.0 / self.sampling_fps
        candidate_timestamps = list(np.arange(t_start, t_end + dense_interval / 2, dense_interval))

        candidate_timestamps.append(t_0)
        candidate_timestamps = sorted(list(set(np.round(candidate_timestamps, 4))))

        omega = []
        anchor_frame_data = anchor.get("frame_data")
        anchor_f_idx = anchor.get("frame_index")

        if anchor_f_idx is not None and anchor_frame_data is not None:
            self._frame_cache[anchor_f_idx] = anchor_frame_data
            if anchor_f_idx not in self._vector_cache:
                self._vector_cache[anchor_f_idx] = self._frame_to_unit_vector(anchor_frame_data)

        target_f_indices = [int(round(ts * fps)) for ts in candidate_timestamps]
        target_f_indices = list(dict.fromkeys(target_f_indices))
        if anchor_f_idx is not None:
            # Keep only frames from the anchor through the frame before the
            # next anchor. The preceding frame is outside D*.
            first_allowed = int(anchor_f_idx)
            end_exclusive = int(np.ceil(t_end * fps))
            target_f_indices = [
                idx for idx in target_f_indices
                if first_allowed <= idx < end_exclusive
            ]
        missing_indices = sorted(list(set(idx for idx in target_f_indices if idx not in self._frame_cache)))

        if missing_indices:
            for idx in missing_indices:
                if 0 <= self._current_cap_pos <= idx and (idx - self._current_cap_pos) <= 30:
                    while self._current_cap_pos < idx:
                        ret, _ = cap.read()
                        if not ret:
                            break
                        self._current_cap_pos += 1
                    ret, frame = cap.read()
                    if ret:
                        self._current_cap_pos += 1
                        self._frame_cache[idx] = frame
                        self._vector_cache[idx] = self._frame_to_unit_vector(frame)
                else:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                    ret, frame = cap.read()
                    if ret:
                        self._current_cap_pos = idx + 1
                        self._frame_cache[idx] = frame
                        self._vector_cache[idx] = self._frame_to_unit_vector(frame)

        for f_idx in target_f_indices:
            if f_idx not in self._frame_cache:
                continue
            frame = self._frame_cache[f_idx]
            v_t = self._vector_cache.get(f_idx)
            if v_t is None:
                v_t = self._frame_to_unit_vector(frame)
                self._vector_cache[f_idx] = v_t

            is_anchor_frame = bool(f_idx == anchor_f_idx)
            omega.append({
                "frame_index": f_idx,
                "time_sec": round(f_idx / fps, 4),
                "is_anchor": is_anchor_frame,
                "vec": v_t,
                "frame_data": frame
            })

        if not omega:
            if anchor_frame_data is not None:
                v_t = self._frame_to_unit_vector(anchor_frame_data)
                omega = [{
                    "frame_index": anchor.get("frame_index", 0),
                    "time_sec": t_0,
                    "is_anchor": True,
                    "vec": v_t,
                    "frame_data": anchor_frame_data
                }]
            else:
                return []

        f_t0 = None
        for item in omega:
            if item["is_anchor"]:
                f_t0 = item
                break
        if f_t0 is None:
            f_t0 = min(omega, key=lambda it: abs(it["time_sec"] - t_0))
            f_t0["is_anchor"] = True

        D = [f_t0]
        selected_indices = {f_t0["frame_index"]}

        target_count = (
            self.target_num_frames
            if target_num_frames is None
            else max(1, int(target_num_frames))
        )
        k_needed = min(target_count - 1, len(omega) - 1)

        before = [item for item in omega if item["time_sec"] < t_0]
        after = [item for item in omega if item["time_sec"] > t_0]
        coverage_candidates = []
        if before:
            coverage_candidates.append(min(before, key=lambda item: abs(item["time_sec"] - t_0)))
        if after:
            coverage_candidates.append(min(after, key=lambda item: item["time_sec"]))
        for candidate in coverage_candidates[:k_needed]:
            D.append(candidate)
            selected_indices.add(candidate["frame_index"])
        k_needed -= min(k_needed, len(coverage_candidates))

        for _ in range(k_needed):
            best_cand = None
            best_min_dist = -1.0

            for cand in omega:
                if cand["frame_index"] in selected_indices:
                    continue

                distances = [
                    float(np.linalg.norm(cand["vec"] - selected["vec"]))
                    for selected in D
                ]
                min_dist = min(distances) if distances else 0.0

                if min_dist > best_min_dist:
                    best_min_dist = min_dist
                    best_cand = cand

            if best_cand is not None:
                D.append(best_cand)
                selected_indices.add(best_cand["frame_index"])

        D.sort(key=lambda item: item["time_sec"])
        return D
