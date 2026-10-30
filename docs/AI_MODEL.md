# AI Model Guide

## Real pipeline

The backend adapter in `backend/src/app/ai/nsfw.py` launches
`proposed/proposed_adult_video_detect.py` as a subprocess. It requires:

- MobileNetV3 Keras model:
  `models/mobilenetv3_small_adult_normal.keras`
- ResNet-50 FCN checkpoint:
  `models/resnet50_adult_normal_fcn_layer4_classifier.pth`
- TensorFlow/Keras, PyTorch, OpenCV, and NumPy.

The model directory is ignored by Git. Model artifacts must be supplied
separately on each development machine.

## Configuration

```dotenv
AI_ANALYSIS_MODE=required
NSFW_PIPELINE_DIR=NSFW-Detection/src
NSFW_PYTHON=
NSFW_TIMEOUT_SECONDS=600
```

Modes:

- `required`: real detector is mandatory; unavailable/error means failed job.
- `auto`: real detector first, then development mock fallback if unavailable.
- `off`: mock-only behavior.

Use `required` to prove real inference. A successful HTTP upload alone is not
proof that the model ran.

## Preprocessing and decision path

The proposed pipeline samples video frames using HSV/Bhattacharyya heuristics,
scores candidate frames with MobileNet at `224x224` RGB normalized to
`[-1, 1]`, selects diverse frames, then evaluates them with the ResNet FCN.
The evaluator combines sustained and flash branches into `NORMAL` or `ADULT`.

The backend converts `ADULT` into an `Adult` label and `pending_review`.
`NORMAL` creates a `Safe` label and publishes under the current business rule.

## Verified evidence

On 2026-10-28, `Travel_4.mp4` was processed with the real models on CPU:

- 256 frames, 8.53 seconds, 10 anchors.
- MobileNet and ResNet loaded and warmed up.
- Decision `NORMAL`, zero Adult regions.
- Total processing time 11.35 seconds.
- Backend API job reached `succeeded`.
- Neon stored `Safe`, confidence `0.0014`, level `LOW`, and `published`.
- Newman real-model collection: 18 requests, 23 assertions, zero failures.

This is a runtime capability result, not a model accuracy evaluation. There
is no verified ground-truth dataset in the workspace, so accuracy, precision,
recall, F1, and confusion matrix are not reported.

## Limitations and safety

Violence, sound, and text/STT detectors are placeholders. The current code
publishes a no-detection result even when Safe confidence is low. Changing that
rule requires an explicit product decision. Do not download or replace models
without approval and provenance.
