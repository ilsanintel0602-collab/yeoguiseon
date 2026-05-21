# Phase B2 — Colab 셀 강화 패치 (전처리·학습·변환)
> **선행**: `colab_cell_patches_B1.md` (B1 인증·다운로드) 완료 후 적용
> **이 패치가 해결하는 위험**:
> (a) AI Hub 데이터가 **분할 압축**으로 와서 머지·해제 단계 필요 — 기존 노트북에 빠짐
> (b) Colab 무료 12h 끊김 — 학습 셀에 **resume + 자동 checkpoint** 추가
> (c) `onnx-tf` 호환성 깨지기 쉬움 — **ultralytics 직접 export 우선**, 실패 시 폴백
> **출처**: https://aihub.or.kr/aihubdata/data/view.do?dataSetSn=71385

---

## 🔧 보강 셀 #4 — cell-8 다음에 추가 (분할 파일 머지 + 해제)

```python
# AI Hub은 큰 파일을 .part1, .part2 등으로 분할 다운로드
# 다운로드 완료 후 머지 + 압축 해제 필요
import subprocess, glob, os
os.chdir('/content/aihub_data')

# 1) 분할 파일 머지 (.part 1,2,3 -> .tar 또는 .zip)
parts = sorted(glob.glob('*.part*'))
print(f'분할 파일 수: {len(parts)}')
if parts:
    # 기본 prefix 추출 (예: 재활용선별장_A2_part1 -> 재활용선별장_A2)
    prefixes = sorted(set(p.rsplit('.part', 1)[0] for p in parts))
    for prefix in prefixes:
        out_name = prefix  # 합쳐진 최종 파일명
        print(f'\n=== 머지: {prefix}.part* → {out_name} ===')
        !cat "{prefix}".part* > "{out_name}"
        !ls -lh "{out_name}"

# 2) 압축 해제 (tar.gz 또는 zip)
for f in sorted(glob.glob('*')):
    if f.endswith('.tar'):
        print(f'tar 해제: {f}'); !tar -xf "{f}"
    elif f.endswith('.tar.gz') or f.endswith('.tgz'):
        print(f'tar.gz 해제: {f}'); !tar -xzf "{f}"
    elif f.endswith('.zip'):
        print(f'zip 해제: {f}'); !unzip -q "{f}"

# 3) 구조 확인
!find /content/aihub_data -maxdepth 3 -type d | head -30
!find /content/aihub_data -name '*.jpg' | wc -l
!find /content/aihub_data -name '*.json' | wc -l
print('\n✅ 이미지 / JSON 수 위에 표시. JSON > 0 이어야 다음 셀 진행 가능.')
```

---

## 🔧 교체 셀 #5 — cell-10 클래스 매핑 (출처 확정)

```python
# AI Hub #71385 공식 9개 카테고리 (출처: 데이터셋 view 페이지)
# 라벨 JSON의 class_name 접두사 → YOLO 클래스 ID
import json, os
from pathlib import Path

# 출처: https://aihub.or.kr/aihubdata/data/view.do?dataSetSn=71385
CLASSES = {
    'c_1':    0,  # 종이
    'c_2_01': 1,  # 종이팩 (일반)
    'c_2_02': 1,  # 종이팩 (멸균) — 동일 처리
    'c_3':    2,  # 캔류
    'c_5_01': 3,  # 페트 (투명)
    'c_5_02': 3,  # 페트 (유색) — 동일 클래스
    'c_6':    4,  # 플라스틱
    'c_7':    5,  # 비닐
    'c_4_01': 6,  # 유리병 (투명)
    'c_4_02': 6,  # 유리병 (갈색)
    'c_4_03': 6,  # 유리병 (녹색)
    'c_8_01': 7,  # 흰색 스티로폼
    'c_8_02': 7,  # 컬러 스티로폼
    'c_9':    8,  # 건전지
}
CLASS_NAMES = ['paper', 'paper_pack', 'can', 'pet', 'plastic', 'vinyl', 'glass', 'styrofoam', 'battery']

DATA_ROOT = '/content/aihub_data'
YOLO_ROOT = '/content/yolo_data'

def class_id_from_name(cls_name: str):
    """class_name 접두사 매칭 → YOLO ID. 없으면 None."""
    for prefix, cid in CLASSES.items():
        if cls_name.startswith(prefix):
            return cid
    return None

def convert_one(json_path: Path, img_w: int, img_h: int) -> list[str]:
    """JSON 1개 → YOLO txt 라인 리스트"""
    with open(json_path, encoding='utf-8') as f:
        d = json.load(f)
    out = []
    for obj in d.get('objects', d.get('annotations', [])):
        cid = class_id_from_name(obj.get('class_name', obj.get('label', '')))
        if cid is None:
            continue
        ann = obj.get('annotation', [{}])
        if isinstance(ann, list) and ann:
            ann = ann[0]
        coord = ann.get('coord') if isinstance(ann, dict) else None
        if not coord:
            # 다른 스키마 가능성: bbox = [x,y,w,h]
            bbox = obj.get('bbox') or obj.get('points')
            if not bbox or len(bbox) < 4:
                continue
            x, y, w, h = bbox[:4]
        else:
            x = coord.get('x', 0); y = coord.get('y', 0)
            w = coord.get('width', 0); h = coord.get('height', 0)
        cx = (x + w/2) / img_w; cy = (y + h/2) / img_h
        nw = w / img_w; nh = h / img_h
        if 0 <= cx <= 1 and 0 <= cy <= 1 and nw > 0 and nh > 0:
            out.append(f'{cid} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}')
    return out

print('✅ 변환 함수 + 9 클래스 매핑 준비됨. 다음 셀에서 분할·변환 일괄 실행.')
```

---

## 🔧 교체 셀 #6 — cell-11 일괄 변환 (이미지 ↔ JSON 페어링 + 8:1:1 분할)

```python
# 이미지 ↔ JSON 페어 매칭 + 변환 + 8:1:1 분할
from PIL import Image
from glob import glob
from sklearn.model_selection import train_test_split
import shutil, json
from pathlib import Path

# 모든 이미지 찾기 (jpg/jpeg/png)
img_paths = []
for ext in ('jpg','jpeg','png'):
    img_paths.extend(glob(f'{DATA_ROOT}/**/*.{ext}', recursive=True))
img_paths = sorted(img_paths)
print(f'이미지 수: {len(img_paths)}')

# JSON 매칭 — 같은 stem(이름) + 동일/상위 폴더의 json 찾기
def find_json_for(img_path: str) -> str | None:
    stem = Path(img_path).stem
    parent = Path(img_path).parent
    # 1) 같은 폴더
    j = parent / f'{stem}.json'
    if j.exists(): return str(j)
    # 2) 부모 폴더 옆 labels/
    for cand in [parent.parent / 'labels' / f'{stem}.json',
                 parent.parent.parent / 'labels' / f'{stem}.json']:
        if cand.exists(): return str(cand)
    # 3) glob 폴백 (느림)
    hits = glob(f'{DATA_ROOT}/**/{stem}.json', recursive=True)
    return hits[0] if hits else None

# 페어 + 변환
paired = []
skipped = 0
for img in img_paths:
    j = find_json_for(img)
    if not j:
        skipped += 1
        continue
    paired.append((img, j))
print(f'페어링 성공: {len(paired)}, 스킵: {skipped}')

# 8:1:1 분할
train, temp = train_test_split(paired, test_size=0.2, random_state=42)
val, test = train_test_split(temp, test_size=0.5, random_state=42)
splits = {'train': train, 'val': val, 'test': test}
print(f'train: {len(train)}, val: {len(val)}, test: {len(test)}')

# 변환 + 복사
for split, items in splits.items():
    img_out = Path(YOLO_ROOT) / 'images' / split
    lbl_out = Path(YOLO_ROOT) / 'labels' / split
    img_out.mkdir(parents=True, exist_ok=True)
    lbl_out.mkdir(parents=True, exist_ok=True)
    converted = 0
    for img_path, json_path in items:
        try:
            with Image.open(img_path) as im:
                w, h = im.size
            lines = convert_one(Path(json_path), w, h)
            if not lines:
                continue  # 라벨 0개 이미지는 스킵
            stem = Path(img_path).stem
            shutil.copy(img_path, img_out / Path(img_path).name)
            (lbl_out / f'{stem}.txt').write_text('\n'.join(lines))
            converted += 1
        except Exception as e:
            pass  # 깨진 이미지/JSON 스킵
    print(f'  {split}: 변환 완료 {converted}')

print('\n✅ YOLO 형식 변환 완료. /content/yolo_data 구조 확인:')
!find /content/yolo_data -maxdepth 2 -type d
```

---

## 🔧 교체 셀 #7 — cell-14 학습 (resume + 자동 checkpoint, Colab 끊김 대응)

```python
# YOLOv8 Small 학습 + 끊김 자동 재개
# Colab 무료는 12h 후 끊김 → /content/runs는 사라지지만 Drive에 마운트하면 영구 보관
from ultralytics import YOLO
import os

# 옵션: Google Drive 마운트해서 checkpoint를 영구 저장 (강력 권장)
USE_DRIVE = True
if USE_DRIVE:
    from google.colab import drive
    drive.mount('/content/drive')
    PROJECT_DIR = '/content/drive/MyDrive/yeoguiseon_yolo_runs'
    os.makedirs(PROJECT_DIR, exist_ok=True)
else:
    PROJECT_DIR = '/content/runs'

RUN_NAME = 'yeoguiseon_v6'
LAST_CKPT = f'{PROJECT_DIR}/detect/{RUN_NAME}/weights/last.pt'

# 자동 resume: last.pt 있으면 이어서, 없으면 pretrained부터 시작
if os.path.exists(LAST_CKPT):
    print(f'🔁 이전 학습 발견 — {LAST_CKPT} 에서 resume')
    model = YOLO(LAST_CKPT)
    resume = True
else:
    print('🆕 새 학습 시작 (yolov8s.pt pretrained)')
    model = YOLO('yolov8s.pt')
    resume = False

# 학습 (Colab T4: batch 16 안전, V100/A100이면 32~64)
results = model.train(
    data=f'{YOLO_ROOT}/dataset.yaml',
    epochs=100,
    imgsz=640,
    batch=16,
    name=RUN_NAME,
    project=f'{PROJECT_DIR}/detect',
    patience=15,
    save=True,
    save_period=5,    # 매 5 epoch마다 checkpoint 저장
    plots=True,
    device=0,
    resume=resume,
    exist_ok=True,    # 같은 이름 재사용 허용
)

print(f'\n✅ 학습 완료. best.pt 위치: {PROJECT_DIR}/detect/{RUN_NAME}/weights/best.pt')
```

> 💡 **끊김 시 재개 절차**: 새 Colab 세션 → cell-0~5 (환경·인증) → 데이터 다운/해제 셀 스킵 (이미 Drive에 있으면 재사용) → 이 셀 그대로 재실행 → `last.pt` 발견 → 자동 resume

---

## 🔧 교체 셀 #8 — cell-18 TF.js 변환 (ultralytics 우선, 실패 시 폴백)

```python
# ultralytics 8.2+ 는 TFJS 직접 export 지원. 안 되면 ONNX → TF → TFJS 폴백.
from ultralytics import YOLO
import os, shutil

BEST = f'{PROJECT_DIR}/detect/{RUN_NAME}/weights/best.pt'
OUT_DIR = '/content/yeoguiseon_yolo_tfjs'
os.makedirs(OUT_DIR, exist_ok=True)
model = YOLO(BEST)

# === Path A: ultralytics 직접 TF.js export (간단, 권장) ===
tfjs_ok = False
try:
    out = model.export(format='tfjs', imgsz=640, int8=False, half=False)
    # ultralytics가 만든 폴더를 OUT_DIR로 복사
    src = str(out) if not str(out).endswith('.pt') else os.path.dirname(BEST)
    !cp -r {src} {OUT_DIR}/ 2>&1 | head -5
    tfjs_ok = True
    print(f'✅ ultralytics 직접 TFJS export 성공: {out}')
except Exception as e:
    print(f'⚠️ ultralytics TFJS export 실패 ({e}). 폴백 시작.')

# === Path B (폴백): ONNX → TF SavedModel → TFJS ===
if not tfjs_ok:
    # 1) ONNX export
    onnx_path = model.export(format='onnx', dynamic=False, simplify=True, imgsz=640)
    print(f'ONNX: {onnx_path}')
    # 2) onnx2tf (onnx-tf는 deprecated → onnx2tf가 활발)
    !pip install -q onnx2tf onnx-graphsurgeon sng4onnx tf-keras
    !onnx2tf -i {onnx_path} -o /content/best_tf -ois images:1,3,640,640
    # 3) TFJS
    !pip install -q tensorflowjs==4.*
    !tensorflowjs_converter \
        --input_format=tf_saved_model \
        --output_format=tfjs_graph_model \
        --quantize_uint8 \
        /content/best_tf \
        {OUT_DIR}

# 크기 확인
!du -sh {OUT_DIR}
!ls -la {OUT_DIR}

# 양자화로 50MB 이하면 OK
print('\n목표: < 50MB. 초과면 imgsz=480 또는 yolov8n 재학습 고려.')
```

> **왜 `onnx-tf` 안 쓰나**: `onnx-tf`는 2023부터 사실상 미유지 + TF 2.15+ 와 충돌. `onnx2tf`가 더 활발하고 호환성 좋음.

---

## 🔧 신규 셀 #9 — cell-20 직후 추가 (정확도 시각화 + Confusion Matrix)

```python
# 학습 결과 시각화 (Phase B 통과 판단용)
import matplotlib.pyplot as plt
from IPython.display import Image as IPImage, display

# ultralytics가 자동 생성하는 결과 이미지들
results_dir = f'{PROJECT_DIR}/detect/{RUN_NAME}'

print('=== 학습 곡선 ===')
display(IPImage(f'{results_dir}/results.png'))

print('\n=== Confusion Matrix ===')
display(IPImage(f'{results_dir}/confusion_matrix.png'))

print('\n=== Val 배치 예측 예시 ===')
display(IPImage(f'{results_dir}/val_batch0_pred.jpg'))

# 9 클래스별 mAP 출력
metrics = YOLO(BEST).val(data=f'{YOLO_ROOT}/dataset.yaml', split='test')
print(f'\n전체 mAP@0.5: {metrics.box.map50:.3f} (목표: 0.85+)')
for i, name in enumerate(CLASS_NAMES):
    m = metrics.box.maps[i] if i < len(metrics.box.maps) else 0
    flag = '✅' if m >= 0.85 else '⚠️' if m >= 0.70 else '❌'
    print(f'  {flag} {name}: {m:.3f}')
```

---

## ➡️ Phase B 통과 기준 (강화)

| 항목 | 통과 기준 |
|---|---|
| 데이터 다운/해제 | JSON > 100K개, 이미지 > 100K개 |
| 페어링 성공률 | > 95% (스킵 비율 < 5%) |
| 전체 mAP@0.5 | ≥ 0.85 |
| 클래스별 최저 mAP | ≥ 0.70 (낮으면 데이터 불균형 → augmentation 강화) |
| TF.js 모델 크기 | ≤ 50MB |
| TF.js 변환 후 정확도 손실 | ≤ 3%p |

미달 시 자동 대응:
- mAP 낮음 → epoch +50, 데이터 augmentation 추가, 또는 yolov8m으로 업
- TF.js 크기 초과 → `imgsz=480` 재학습 또는 `yolov8n` 사용
- 페어링 낮음 → 다른 폴더 구조 가능성 → cell-11 `find_json_for` 추가 케이스
