# Sensitive-Video-Moderation

Dự án cung cấp hai giải pháp Deep Learning phát hiện và kiểm duyệt video có nội dung người lớn/nhạy cảm:
1. **Pipeline đề xuất (Proposed Method - thư mục `proposed/`)**: Kiến trúc phễu phân tầng 4 giai đoạn (4-Stage Hierarchical Cascade) kết hợp lấy mẫu theo histogram HSV và khoảng cách Bhattacharyya, quét thô độ nhạy cao MobileNetV3-Small, phóng đại không gian 360x640 với chọn mẫu đa dạng cực đại (Max-Min Diversity / FPS), và bộ đánh giá hợp nhất hai nhánh (Sustained NSFW & Flash Insert).
2. **Pipeline tham chiếu (Baseline Paper - thư mục `baseline/`)**: Phương pháp từ bài báo tham chiếu dựa trên xử lý dòng (Stream) On-device, kết hợp bộ lọc trùng lặp khung hình SSIM và phân loại thời gian thực bằng MobileNetV3.

---

## Mục Lục
- [Sensitive-Video-Moderation (PBL6)](#sensitive-video-moderation-pbl6)
  - [Mục Lục](#mục-lục)
  - [1. Yêu Cầu Môi Trường \& Cài Đặt](#1-yêu-cầu-môi-trường--cài-đặt)
    - [1.1. Yêu cầu hệ thống](#11-yêu-cầu-hệ-thống)
    - [1.2. Khởi tạo môi trường ảo và cài đặt thư viện](#12-khởi-tạo-môi-trường-ảo-và-cài-đặt-thư-viện)
  - [2. Cấu Hình Biến Môi Trường (.env)](#2-cấu-hình-biến-môi-trường-env)
  - [3. Tóm Tắt Luồng Hoạt Động](#3-tóm-tắt-luồng-hoạt-động)
    - [3.1. Pipeline Đề Xuất (Proposed Method - 4 Giai Đoạn)](#31-pipeline-đề-xuất-proposed-method---4-giai-đoạn)
    - [3.2. Pipeline Tham Chiếu (Baseline Paper)](#32-pipeline-tham-chiếu-baseline-paper)
    - [3.3. Hỗ trợ 3 Tỉ lệ Khung hình Chuẩn (16:9, 9:16, 1:1)](#33-hỗ-trợ-3-tỉ-lệ-khung-hình-chuẩn-169-916-11)
  - [4. Hướng Dẫn Thực Thi \& Tham Số Dòng Lệnh](#4-hướng-dẫn-thực-thi--tham-số-dòng-lệnh)
    - [4.1. Chạy Pipeline Đề Xuất (Proposed)](#41-chạy-pipeline-đề-xuất-proposed)
      - [Bảng tham số `proposed_adult_video_detect.py`:](#bảng-tham-số-proposed_adult_video_detectpy)
    - [4.2. Cắt Clip Vi Phạm (Proposed)](#42-cắt-clip-vi-phạm-proposed)
    - [4.3. Chạy Pipeline Tham Chiếu (Baseline)](#43-chạy-pipeline-tham-chiếu-baseline)
    - [4.4. Cắt Clip Vi Phạm (Baseline)](#44-cắt-clip-vi-phạm-baseline)
  - [5. Đánh Giá Thực Nghiệm & Bộ Benchmark (E1 - E7)](#5-đánh-giá-thực-nghiệm--bộ-benchmark-e1---e7)
    - [5.1. Lệnh thực thi Benchmark](#51-lệnh-thực-thi-benchmark)
    - [5.2. Kết quả thực nghiệm chi tiết](#52-kết-quả-thực-nghiệm-chi-tiết)

---

## 1. Yêu Cầu Môi Trường & Cài Đặt

### 1.1. Yêu cầu hệ thống
- **Hệ điều hành**: Linux (Ubuntu, Debian, Fedora, Arch) hoặc Windows.
- **Python**: Sử dụng `Python 3.12.x`, là phiên bản được khóa trong
  `pyproject.toml` để tương thích với TensorFlow 2.20.0, Keras 3.13.2 và
  PyTorch trong cùng môi trường.
- **Phần cứng**: Hỗ trợ chạy trên cả CPU và GPU (NVIDIA GPU với CUDA hỗ trợ tăng tốc tối đa).
- **Yêu cầu bổ sung**: Cài đặt sẵn `ffmpeg` trên hệ thống nếu cần cắt/xuất clip; giai đoạn lấy mẫu không cần `ffprobe`.
- **Bộ dữ liệu video**: nằm ở `local/TestDataset-v2/` (gồm `Adult/` và `Normal/`) ở thư mục gốc repo — thư mục `local/` bị Git bỏ qua.

### 1.2. Khởi tạo môi trường ảo và cài đặt thư viện

Chạy từ thư mục `backend\NSFW-Detection\src`:

```powershell
uv sync
uv run python proposed\proposed_adult_video_detect.py --help
```

### Cài đặt GPU cho cả MobileNetV3 và ResNet-50 (Linux/WSL2 + NVIDIA)

Mặc định, chương trình chọn GPU nếu cả backend nhận diện được, nếu không sẽ dùng CPU. MobileNetV3 chạy qua TensorFlow; ResNet-50 chạy qua PyTorch. Vì vậy chỉ cài PyTorch CUDA là **chưa đủ**: TensorFlow cũng phải nhận diện GPU.

```bash
# Chạy từ thư mục backend\NSFW-Detection\src
uv sync

# TensorFlow 2.20 dùng CUDA 12.5/cuDNN 9.3; dùng PyTorch CUDA 12.4 (cuDNN 9.x).
# --no-deps tránh để uv thay thế các gói NVIDIA dùng chung đã được cài cho TensorFlow.
uv pip install --no-deps torch==2.6.0 --index-url https://download.pytorch.org/whl/cu124

# Xác minh cả backend, GPU và khả năng nạp mô hình MobileNet thực tế
cd src
PROJ6_DEVICE=cuda python check_gpu.py
cd ..
```

**Lý do nâng phiên bản:** file mô hình `mobilenetv3_small_adult_normal.keras` ghi metadata `keras_version=3.13.2`. Vì vậy, không dùng TensorFlow 2.15/Keras 2 cho mô hình này. Code suy luận đã được đổi sang `load_model(..., compile=False)` vì optimizer/loss không cần thiết khi chỉ phân loại.

Cần có driver NVIDIA tương thích và TensorFlow GPU hỗ trợ trên Linux hoặc WSL2. TensorFlow từ phiên bản 2.11 trở lên không hỗ trợ CUDA GPU trên Windows native; trên Windows hãy dùng WSL2 hoặc chạy CPU. Nếu `check_gpu.py` báo lỗi, không nên xem kết quả benchmark là GPU cho tới khi cả hai backend và mô hình MobileNet được xác nhận.

Điều khiển thiết bị:
```bash
# Tự động: GPU nếu backend thấy GPU, nếu không thì CPU
PROJ6_DEVICE=auto python benchmark/run_all_benchmarks.py --force-rerun

# Bắt buộc cả TensorFlow và PyTorch dùng GPU; lỗi sớm nếu một bên không nhận GPU
python benchmark/run_all_benchmarks.py --device cuda --force-rerun

# Chạy đối chứng CPU
python benchmark/run_all_benchmarks.py --device cpu --force-rerun
```

**Lưu ý benchmark:** phải chạy lại toàn bộ bài đo khi đổi CPU/GPU. Không so trực tiếp thời gian CPU cũ với GPU mới nếu chưa ghi nhận chế độ thiết bị và chạy warm-up tương đương.

---

## 2. Cấu Hình Biến Môi Trường (.env)

Tệp `.env` đặt tại thư mục `src/` quản lý các đường dẫn mô hình và thư mục đầu ra:

```env
# ============================================================
# CẤU HÌNH PIPELINE PROPOSED (PHƯƠNG PHÁP ĐỀ XUẤT)
# ============================================================
RESNET_MODEL=models/resnet50_adult_normal_fcn_layer4_classifier.pth
MOBILENET_MODEL=models/mobilenetv3_small_adult_normal.keras
PROPOSED_MODEL=models/resnet50_adult_normal_fcn_layer4_classifier.pth

PROPOSED_OUT_DIR=../ProposedLog
PROPOSED_CLIPS_OUT_DIR=../proposed_bad_clips
RESNET_OUT_DIR=../ProposedLog
RESNET_CLIPS_OUT_DIR=../proposed_bad_clips

# ============================================================
# CẤU HÌNH PIPELINE BASELINE (PHƯƠNG PHÁP PAPER THAM CHIẾU)
# ============================================================
BASELINE_MODEL=models/mobilenetv3_small_adult_normal.keras

BASELINE_OUT_DIR=../BaselineLog
BASELINE_CLIPS_OUT_DIR=../baseline_bad_clips
MOBILENET_OUT_DIR=../BaselineLog
MOBILENET_CLIPS_OUT_DIR=../baseline_bad_clips
```

---

## Ghi chú về bộ lấy mẫu giai đoạn 1

Bản hiện tại **không phân tích miền nén bitstream** và không trích xuất I-frame. Bộ lấy mẫu chỉ dùng histogram màu HSV và khoảng cách Bhattacharyya; Z-score được tính từ chuỗi khoảng cách để tìm biến động bất thường. Khoảng cách lớn cũng được dùng như heuristic ước lượng ranh giới cảnh, nên cần đánh giá độ chính xác riêng nếu báo cáo shot-boundary detection.

### Cập nhật nhánh Flash và Sustained

- Nhánh Flash lấy frame trong đoạn `[anchor hiện tại, anchor kế tiếp)`, giữ anchor
  và bổ sung bằng Greedy Max-Min Diversity. `D*` không chứa frame trước anchor
  hoặc frame tại/sau anchor kế tiếp.
- Nhánh Sustained bắt đầu với 3 frame, tăng 1 frame cho mỗi giây của đoạn,
  tối đa 32 frame và không vượt số frame thực tế có thể lấy.
- E7 báo cáo recall cấp video trên toàn bộ `local/TestDataset-v2/Adult` và
  `local/TestDataset-v2/Normal`; manifest E5 chỉ được dùng khi truyền tường minh
  `--manifest`.

## 3. Tóm Tắt Luồng Hoạt Động

### 3.1. Pipeline Đề Xuất (Proposed Method - 4 Giai Đoạn)

**Cách chạy (năm 2024+):** bốn giai đoạn được **chép lên nhau theo từng frame** trong
module dùng chung [`proposed/streaming_cascade.py`](proposed/streaming_cascade.py)
(`run_cascade()`), thay vì “decode hết video → suy luận hết → mới đánh giá anchor”:

- decode từng frame → Stage 1 chọn mẫu → đủ `batch_size` (mặc định 32) mẫu là chạy MobileNet ngay;
- anchor đã có **anchor kế tiếp** là đánh giá Stage 3 + Stage 4 ngay (không chờ hết video);
- gặp anchor ADULT và `--early_stop` (mặc định bật) là **dừng luôn vòng decode**;
- một anchor chỉ được đánh giá khi đã biết anchor kế tiếp nên tập D* vẫn là `[t_i, t_i+1)` —
  kết quả từng anchor không đổi so với bản chạy hết video.

CLI `proposed_adult_video_detect.py` và benchmark **E3/E4** đều gọi chung `run_cascade()`,
nên số liệu benchmark phản ánh đúng bản đang chạy. E2/E5/E7 vẫn giữ nguyên cách gọi
`sample_video()` + `filter_candidates()` (quét hết video) cho mục đích đo riêng của từng thí nghiệm.

```
[Video Input (Hỗ trợ 16:9, 9:16, 1:1)] — decode tuần tự, dừng ngay khi có phán quyết
      │
      ▼
[Giai Đoạn 1: Histogram HSV và khoảng cách Bhattacharyya]
      ├─ Đọc frame tuần tự và tính histogram màu HSV 16×16 trên ảnh 64×64
      ├─ Tính khoảng cách Bhattacharyya giữa histogram HSV của các frame liên tiếp
      ├─ Tính Z-score đột biến trên sliding window W = 15: Z_flash(t)
      └─ Chọn mẫu theo khoảng thời gian tối đa, Z-score khoảng cách HSV và khoảng cách lớn gợi ý ranh giới cảnh
      │   (Xử lý luồng: frame_data chỉ giữ tới khi suy luận xong → RAM không tăng theo độ dài video)
      │
      ▼
[Giai Đoạn 2: Quét thô Độ nhạy cao với MobileNetV3-Small]
      ├─ Resize trực tiếp 224x224, chạy theo lô Batch_Size = 32
      ├─ Nếu p_mobile(t) < 0.35: Loại bỏ sớm (Early Rejection)
      └─ Nếu p_mobile(t) >= 0.35: Đưa vào tập tâm điểm nghi vấn (Anchor Set A)
      │
      ▼
[Kiểm tra Anchor Set A]
      ├─ Nếu A rỗng ──► KẾT THÚC SỚM (Toàn bộ video = NORMAL) [Tốc độ 200-500 FPS]
      │
      └─ Nếu có Anchor: đánh giá mốc t_0 ngay khi đã biết anchor kế tiếp
            (anchor cuối dùng thời lượng video làm ranh giới — chỉ chốt khi hết video):
            ├─ [Giai Đoạn 3: Phóng đại Không gian & Max-Min Diversity]
            │     ├─ Lấy frame trong [anchor hiện tại, anchor kế tiếp), giữ anchor; không lấy frame ngoài khoảng
            │     ├─ Chuẩn hóa ảnh xám 32x32 thành vector đơn vị ||v||_2 = 1
            │     ├─ Thuật toán Greedy Farthest Point Sampling chọn tập D* gồm 5 frames
            │     └─ Dự đoán xác suất ResNet-50 FCN ở độ phân giải cao 360x640 (Feature grid 12x20=240)
            │
            └─ [Giai Đoạn 4: Bộ Đánh giá Hợp nhất Hai Nhánh]
                  ├─ Nhánh 1 (Sustained NSFW): P_mean >= 0.85 VÀ tỷ lệ frames >= 0.80 đạt 0.60
                  ├─ Nhánh 2 (Flash Insert):
                  │     (1) Cách nhanh: |D*| <= 5 VÀ P_mean(D*) >= 0.90; hoặc
                  │     (2) Z_flash(t_0) > 3.0 và đồng thuận MobileNet/ResNet tại anchor
                  └─ Decision(t_0) = ADULT nếu Nhánh 1 = True HOẶC Nhánh 2 = True
      │
      ▼
[Phán quyết Video: ADULT / NORMAL] ───► Lưu báo cáo 08_final_decision.json
```

### 3.2. Pipeline Tham Chiếu (Baseline Paper)

Chiến lược **Xử lý dòng On-device + Lọc SSIM + Suy luận thời gian thực**:

```
[Video Input]
      │
      ▼
[Bước 1: Frame Extractor Stream] ─────► Đọc tuần tự từng frame dưới dạng Generator trên RAM
      │
      ▼
[Bước 2: SSIM Filter Stream] ─────────► Thu nhỏ ảnh về 224x224 & tính SSIM giữa Frame(t) và Frame(t-1)
      │                                 └─ Loại bỏ khung hình trùng lặp
      ▼
[Bước 3: MobileNetV3 Batch Inference] ─► Gom batch, resize trực tiếp 224x224
      │                                 └─ Dự đoán nhãn Adult / Normal
      ▼
[Bước 4: Evaluator] ──────────────────► Xác định Video = Adult nếu có frame vi phạm
                                        Lưu kết quả vào 12_final_decision.json
```

#### Tham số thực tế của Baseline

| Hạng mục | Cấu hình thực tế | Hành vi trong chương trình |
| :--- | :--- | :--- |
| Kích thước ảnh tính SSIM | `224 x 224` | Frame được đổi sang grayscale rồi resize bằng `INTER_LINEAR` trước khi tính SSIM |
| Frame tham chiếu | Frame được giải mã ngay trước đó | So sánh `Frame(t)` với `Frame(t-1)` theo thứ tự decode, không phải frame gần nhất đã được giữ lại |
| Ngưỡng SSIM | `0.95` | Giữ frame khi `SSIM < 0.95`; loại frame khi `SSIM >= 0.95` |
| Chiều so sánh | Độ tương đồng cao là frame trùng lặp | SSIM càng cao càng dễ bị loại |
| Tiền xử lý MobileNet | `224 x 224`, BGR → RGB, `float32` | `image = RGB / 127.5 - 1.0`, đưa giá trị về `[-1, 1]` |
| Ngưỡng ADULT | `0.85` | Frame được gán `adult` khi `p_adult >= 0.85` |
| Quy tắc cấp video | Một frame Adult là đủ | Video là `adult` nếu tồn tại ít nhất một frame được gán `adult` |
| Dừng sớm khi chạy CLI | Mặc định tắt | Chỉ dừng ngay sau batch chứa frame Adult đầu tiên khi truyền `--early_stop` |
| Dừng sớm khi benchmark E3/E4 | Bật | Benchmark gọi `predict_stream(..., early_stop=True)` để đo đường đi early-stop |

SSIM luôn cập nhật frame tham chiếu bằng frame vừa giải mã, kể cả khi frame đó
bị loại. Vì vậy, chuỗi so sánh là các frame liên tiếp của video và không bị
đổi thành chuỗi các frame đã giữ lại.

### 3.3. Hỗ trợ 3 Tỉ lệ Khung hình Chuẩn (16:9, 9:16, 1:1)

Hệ thống chấp nhận đúng 3 tỉ lệ chuẩn tương ứng với các cấu hình tensor đầu vào ResNet-50:
- **Portrait (9:16)**: Target kích thước `360x640` $\to$ Feature Grid Layer 4: $12 \times 20 = 240$ vùng.
- **Square (1:1)**: Target kích thước `480x480` $\to$ Feature Grid Layer 4: $15 \times 15 = 225$ vùng.
- **Landscape (16:9)**: Target kích thước `640x360` $\to$ Feature Grid Layer 4: $20 \times 12 = 240$ vùng.

---

## 4. Hướng Dẫn Thực Thi & Tham Số Dòng Lệnh

### 4.1. Chạy Pipeline Đề Xuất (Proposed)
```bash
python proposed/proposed_adult_video_detect.py --video "../../local/TestDataset-v2/Adult/A_01.mp4"
```
*Để kích hoạt dừng sớm ngay khi phát hiện vi phạm Adult đầu tiên:*
```bash
python proposed/proposed_adult_video_detect.py --video "../../local/TestDataset-v2/Adult/A_01.mp4" --early_stop
```

#### Bảng tham số `proposed_adult_video_detect.py`:
| Tham số | Kiểu | Mặc định | Ý nghĩa |
| :--- | :--- | :--- | :--- |
| `--video` | `str` | *Bắt buộc* | Đường dẫn đến file video cần phân tích |
| `--early_stop` | `flag` | `False` | Dừng sớm ngay khi phát hiện anchor vi phạm Adult đầu tiên |
| `--out_dir` | `str` | Lấy từ `.env` | Thư mục lưu kết quả JSON và log (`../ProposedLog`) |
| `--mobilenet_model` | `str` | Lấy từ `.env` | Đường dẫn mô hình MobileNetV3-Small (`.keras`) |
| `--resnet_model` | `str` | Lấy từ `.env` | Đường dẫn mô hình ResNet50 FCN (`.pth`) |
| `--delta_t` | `float` | `0.5` | Khoảng thời gian tối đa giữa các frame lấy mẫu cơ sở |
| `--z_threshold` | `float` | `3.0` | Ngưỡng Z-score phát hiện đột biến flash nhấp nháy |
| `--rejection_threshold` | `float` | `0.35` | Ngưỡng loại bỏ sớm của MobileNetV3 ở Bước 2 |
| `--batch_size` | `int` | `32` | Số lượng frame gom trong một batch suy luận MobileNet |
| `--save_intermediate` | `flag` | `False` | Lưu log đĩa và các frame ảnh ở từng giai đoạn để debug |

---

### 4.2. Cắt Clip Vi Phạm (Proposed)
Sau khi có file `08_final_decision.json`, trích xuất các đoạn video nhạy cảm bằng:
```bash
python proposed/cut_adult_regions.py --json "../ProposedLog/A_01/08_final_decision.json"
```

---

### 4.3. Chạy Pipeline Tham Chiếu (Baseline)
```bash
python baseline/baseline_adult_video_detect.py --video "../../local/TestDataset-v2/Normal/N_01.mp4"
```
*Để kích hoạt dừng sớm ngay khi gặp frame nhạy cảm đầu tiên:*
```bash
python baseline/baseline_adult_video_detect.py --video "../../local/TestDataset-v2/Normal/N_01.mp4" --early_stop
```

---

### 4.4. Cắt Clip Vi Phạm (Baseline)
Sau khi có file `12_final_decision.json`:
```bash
python baseline/cut_adult_regions.py --json "../BaselineLog/N_01/12_final_decision.json"
```

---

## 5. Đánh Giá Thực Nghiệm & Bộ Benchmark (E1 - E4)

### 5.1. Lệnh thực thi Benchmark

Chạy toàn bộ các bài thực nghiệm (E1 $\to$ E6) và tự động tổng hợp báo cáo:
```bash
python ../benchmark/run_all_benchmarks.py
```

Hoặc chạy từng bài thực nghiệm độc lập:
* **E1 - Đánh giá mô hình phân loại frame tĩnh**:
  ```bash
  python ../benchmark/e1_prepare_frames.py
  python ../benchmark/e1_eval_proposed.py
  python ../benchmark/e1_eval_baseline.py
  ```
* **E2 - Đánh giá bộ lọc khung hình Stage 1**:
  ```bash
  python ../benchmark/e2_eval_proposed_stage1.py
  python ../benchmark/e2_eval_baseline_stage1.py
  ```
* **E3 & E4 - Đánh giá toàn bộ Pipeline trên video & Chi phí tính toán**:
  ```bash
  python ../benchmark/e3_e4_eval_proposed.py
  python ../benchmark/e3_e4_eval_baseline.py
  python ../benchmark/e3_eval.py
  ```
* **E5 - Kiểm thử Flash-Insert và ablation**:
  ```bash
  python ../benchmark/e5_prepare_flash_videos.py --seed 2026 --count 100
  python ../benchmark/e5_eval_flash_ablation.py
  python ../benchmark/e5_eval.py
  ```
  Bước chuẩn bị chọn ngẫu nhiên có thể tái lập các video Normal và Adult
  từ dataset theo `--seed`; `--count` quy định số video Flash-Insert được tạo.
  Nếu `--count` lớn hơn số video Normal, nguồn Normal có thể được chọn lặp
  nhưng mỗi ca kiểm thử vẫn có vị trí chèn và file output riêng.
  Seed, danh sách nguồn và vị trí chèn thực tế được lưu trong manifest.

---

### 5.2. Kết quả thực nghiệm chi tiết

E4 ghi trực tiếp luồng số liệu theo từng video, không suy ra số frame Stage 4
bằng phép trừ. Các trường chính trong `e3_e4_proposed_results.json` gồm:

- `stage1_sampled_frames`: số frame được HSV giữ lại từ tổng `raw_frames`;
  nếu pipeline dừng sớm thì đây là số frame **đã quét tới điểm dừng**, kèm cờ
  `stage1_scan_complete` = false để phân biệt;
- `stage2_candidates_in`: số frame thật sự đã chạy qua MobileNet (thấp hơn
  `stage1_sampled_frames` đúng bằng phần lô chưa suy luận khi dừng sớm);
- `stop_reason`: `end_of_video` | `adult_detected` | `no_stage1_samples` |
  `all_candidates_rejected_by_mobilenet`; `inspected_frames` = số frame đã decode;
- `stage2_video_status`, `stage2_stop_reason`: số video
  dừng sau Stage 2 và nguyên nhân;
- `stage3_forwarded_anchors`, `stage3_diverse_frames`: số anchor/frame được
  chuyển tiếp và trích xuất;
- `stage4_resnet_frames`: số frame ResNet-50 FCN thực sự xử lý, cộng từ từng
  lần đánh giá anchor.

E4 xuất thêm `EvaluationResults/e4_summary.md` và
`EvaluationResults/e4_stage_flow.png`. E7 quét các ngưỡng Z-score (mặc định 2, 2.5, 3, 3.5, 4) trên cùng manifest
flash-insert. Với mỗi ngưỡng, E7 chạy toàn bộ cascade Stage 1→4 và đo
wall-clock end-to-end, đồng thời báo cáo recall bắt được flash. Speedup được
tính so với cùng cascade nhưng tắt cổng Z-score (`k=999`), nên phản ánh cả
chi phí MobileNet, lấy mẫu Stage 3 và ResNet/Stage 4 trong
`e7_summary.json`, `e7_summary.md`, và `e7_zscore_speedup_recall.png`.

**Lưu ý:** Các bảng dưới đây là kết quả lịch sử của một lần chạy trên tập dữ liệu cũ (20 video, 14,057 frames). Đây không phải kết quả của dataset hiện tại; hãy chạy lại benchmark để tạo số liệu phù hợp với tập dữ liệu và phần cứng đang dùng.

#### Bảng E1: So sánh mô hình phân loại cấp khung hình (200 frames)
| Chỉ số | Proposed (ResNet-50 FCN) | Baseline (MobileNetV3-Small) |
| :--- | :---: | :---: |
| **Số tham số (Parameters)** | 23.51 M | **0.94 M** |
| **Kích thước mô hình** | 90.01 MB | **8.62 MB** |
| **Độ trễ trung bình 1 frame** | 830.08 ms | **187.29 ms** |
| **Accuracy** | **87.0%** | 85.0% |
| **Precision** | **91.11%** | 86.46% |
| **Recall** | 82.0% | **83.0%** |
| **F1-Score** | **86.32%** | 84.69% |
| **Độ đồng thuận (Agreement)** | \multicolumn{2}{c|}{**91.0%**} |

#### Bảng E2: So sánh bộ lọc khung hình giai đoạn 1 (14,057 frames)
| Chỉ số | Proposed Stage 1 (HSV + Bhattacharyya distance) | Baseline Stage 1 (SSIM Filter 224x224) |
| :--- | :---: | :---: |
| **Tổng frame đầu vào** | 14,057 | 14,057 |
| **Frame được chọn** | **1,141** | 7,947 |
| **Tỉ lệ giảm tải frame** | **91.88%** | 43.47% |
| **Tốc độ thông lượng** | **128.5 FPS** | 91.7 FPS |
| **Thời gian trung bình / video** | **5.47 s** | 7.66 s |

#### Bảng E3: So sánh chất lượng phân loại cấp độ Video
| Chỉ số | Proposed Pipeline (4-Stage Cascade) | Baseline Pipeline (MobileNetV3 + SSIM) |
| :--- | :---: | :---: |
| **True Positive (TP)** | 9 / 10 | **10 / 10** |
| **True Negative (TN)** | **10 / 10** | 4 / 10 |
| **False Positive (FP - Báo giả)** | **0** *(Không báo nhầm video an toàn)* | 6 *(Báo nhầm 6 video an toàn)* |
| **False Negative (FN)** | 1 | **0** |
| **Accuracy** | **95.0%** | 70.0% |
| **Precision** | **100.0%** | 62.5% |
| **Recall** | 90.0% | **100.0%** |
| **F1-Score** | **94.74%** | 76.92% |

#### Bảng E4: Chi phí tính toán & Tỉ lệ giảm tải toàn Pipeline
| Chỉ số | Proposed Pipeline | Baseline Pipeline |
| :--- | :---: | :---: |
| **Tổng số frame chạy qua CNN** | **2,358** | 3,039 |
| **Tỉ lệ giảm frame qua CNN** | **83.23%** | 78.38% |
| **Throughput toàn pipeline** | 29.3 FPS | 220.5 FPS |
