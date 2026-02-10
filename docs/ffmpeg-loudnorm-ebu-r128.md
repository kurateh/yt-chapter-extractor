# ffmpeg loudnorm 필터 & EBU R128 기술 문서

## 목차

1. [EBU R128 표준 개요](#ebu-r128-표준-개요)
2. [핵심 측정 지표](#핵심-측정-지표)
3. [ffmpeg loudnorm 필터](#ffmpeg-loudnorm-필터)
4. [Single-Pass vs Dual-Pass](#single-pass-vs-dual-pass)
5. [Dynamic vs Linear 모드](#dynamic-vs-linear-모드)
6. [본 프로젝트에서의 사용](#본-프로젝트에서의-사용)

---

## EBU R128 표준 개요

EBU R128은 유럽방송연합(European Broadcasting Union)이 2010년 제정한 오디오 라우드니스 정규화 권고안이다. 기존의 피크 기반 레벨 측정이 인간의 청각 인지와 괴리가 있는 문제를 해결하기 위해, **인지적 라우드니스(perceived loudness)** 기반 측정 방식을 정의한다.

### 피크 정규화 vs 라우드니스 정규화

| 방식 | 기준 | 한계 |
|------|------|------|
| **피크 정규화** | 신호의 최대 진폭(peak amplitude) | 동일 피크라도 주파수 특성에 따라 체감 음량이 다름 |
| **라우드니스 정규화** | K-가중(K-weighted) 인지 음량 | 인간 청각에 맞춘 측정으로 실제 체감 음량이 균일 |

EBU R128은 ITU-R BS.1770에 정의된 K-가중 측정 알고리즘을 사용한다. K-가중치는 인간의 귀가 주파수별로 민감도가 다른 특성을 반영한 필터링이다.

### 단위: LUFS와 LU

- **LUFS** (Loudness Units relative to Full Scale): 절대 라우드니스 값. 0 LUFS가 디지털 풀스케일.
- **LU** (Loudness Units): 상대적 라우드니스 차이. 1 LU = 1 dB.
- LUFS와 LKFS는 동일한 단위이다 (LKFS는 ITU 표기, LUFS는 EBU 표기).

### 권장 타겟

- 방송: **-23 LUFS** (허용 오차 ±0.5 LU, 라이브 ±1 LU)
- 스트리밍 플랫폼: -14 LUFS (Spotify, YouTube 등)
- 팟캐스트: -16 ~ -14 LUFS

---

## 핵심 측정 지표

### Integrated Loudness (IL)

전체 오디오의 평균 인지 음량. **게이팅(gating)** 메커니즘으로 무음 구간이 측정을 왜곡하는 것을 방지한다.

**이중 게이팅 방식:**

1. **절대 게이트 (Absolute Gate)**: -70 LUFS 미만 구간을 측정에서 제외. 무음이나 극소음 구간 필터링.
2. **상대 게이트 (Relative Gate)**: 현재 측정된 Integrated Loudness보다 10 LU 낮은 구간을 제외. 상대적으로 조용한 구간 필터링.

```
[전체 오디오]
    → 절대 게이트 (-70 LUFS 미만 제외)
    → 1차 평균 계산
    → 상대 게이트 (1차 평균 - 10 LU 미만 제외)
    → 최종 Integrated Loudness
```

### Loudness Range (LRA)

오디오의 동적 범위를 나타내는 지표. 단위는 LU. 조용한 부분과 큰 부분의 라우드니스 차이를 측정한다.

- **낮은 LRA** (< 5 LU): 일정한 음량 (팟캐스트, 팝 음악)
- **중간 LRA** (5-15 LU): 보통 수준의 동적 범위
- **높은 LRA** (> 15 LU): 넓은 동적 범위 (클래식 음악, 영화 사운드트랙)

### True Peak (TP)

디지털-아날로그 변환 시 실제로 발생할 수 있는 최대 신호 레벨. 샘플 간 보간(inter-sample interpolation)을 통해 디지털 샘플 값 사이에서 발생하는 피크까지 감지한다.

- 일반 피크: 디지털 샘플 값의 최대치만 측정
- **트루 피크**: 샘플 간 보간으로 실제 아날로그 파형의 최대치 추정

EBU R128 권장 최대 True Peak: **-1 dBTP**

---

## ffmpeg loudnorm 필터

ffmpeg의 `loudnorm` 필터는 EBU R128 표준을 구현한 오디오 필터다.

### 전체 파라미터

| 파라미터 | 범위 | 기본값 | 설명 |
|----------|------|--------|------|
| `I` (또는 `i`) | -70.0 ~ -5.0 | -24.0 | 타겟 Integrated Loudness (LUFS) |
| `LRA` (또는 `lra`) | 1.0 ~ 50.0 | 7.0 | 타겟 Loudness Range (LU) |
| `TP` (또는 `tp`) | -9.0 ~ +0.0 | -2.0 | 최대 True Peak (dBTP) |
| `measured_I` | -99.0 ~ +0.0 | — | 측정된 Integrated Loudness (dual-pass용) |
| `measured_LRA` | 0.0 ~ 99.0 | — | 측정된 Loudness Range (dual-pass용) |
| `measured_TP` | -99.0 ~ +99.0 | — | 측정된 True Peak (dual-pass용) |
| `measured_thresh` | -99.0 ~ +0.0 | — | 측정된 게이트 임계값 (dual-pass용) |
| `offset` | -99.0 ~ +99.0 | 0.0 | 리미터 전 오프셋 게인 (LU) |
| `linear` | true / false | true | 선형 스케일링 모드 활성화 |
| `dual_mono` | true / false | false | 모노 입력을 dual-mono로 처리 |
| `print_format` | summary / json / none | none | 측정 결과 출력 형식 |

### 기본 사용법

```bash
# 측정만 수행 (출력 없음)
ffmpeg -i input.mp3 -af loudnorm=print_format=json -f null -

# 기본값으로 정규화 (-24 LUFS, LRA 7, TP -2)
ffmpeg -i input.mp3 -af loudnorm output.mp3

# 커스텀 타겟으로 정규화
ffmpeg -i input.mp3 -af loudnorm=I=-16:LRA=11:TP=-1.5 output.mp3
```

### 측정 결과 JSON 형식

`print_format=json` 사용 시 stderr로 출력되는 JSON:

```json
{
    "input_i": "-28.21",
    "input_tp": "-2.43",
    "input_lra": "14.30",
    "input_thresh": "-38.53",
    "output_i": "-24.02",
    "output_tp": "-2.00",
    "output_lra": "7.30",
    "output_thresh": "-34.52",
    "normalization_type": "dynamic",
    "target_offset": "-0.02"
}
```

| 필드 | 설명 |
|------|------|
| `input_i` | 입력 Integrated Loudness |
| `input_tp` | 입력 True Peak |
| `input_lra` | 입력 Loudness Range |
| `input_thresh` | 입력 게이트 임계값 |
| `output_i` | 출력 Integrated Loudness |
| `output_tp` | 출력 True Peak |
| `output_lra` | 출력 Loudness Range |
| `output_thresh` | 출력 게이트 임계값 |
| `normalization_type` | 적용된 모드 (dynamic / linear) |
| `target_offset` | 타겟 대비 오프셋 |

> **주의**: loudnorm 필터의 JSON 출력은 stdout가 아닌 **stderr**로 출력된다.

---

## Single-Pass vs Dual-Pass

### Single-Pass (1패스)

한 번의 처리로 측정과 정규화를 동시에 수행한다.

```bash
ffmpeg -i input.mp3 -af loudnorm=I=-16:LRA=11:TP=-1.5 output.mp3
```

**특징:**
- 실시간 스트리밍에 적합
- 빠르지만 정밀도가 낮음
- Dynamic 모드로 동작하여 게인이 실시간으로 변동
- 오디오 시작 부분에서 정확도가 떨어질 수 있음

### Dual-Pass (2패스)

1패스에서 측정한 값을 2패스에 전달하여 더 정밀한 정규화를 수행한다.

**Pass 1 — 측정:**

```bash
ffmpeg -i input.mp3 \
  -af loudnorm=I=-16:LRA=11:TP=-1.5:print_format=json \
  -f null -
```

**Pass 2 — 측정값 기반 정규화:**

```bash
ffmpeg -i input.mp3 \
  -af loudnorm=I=-16:LRA=11:TP=-1.5:\
measured_I=-28.21:\
measured_LRA=14.30:\
measured_TP=-2.43:\
measured_thresh=-38.53:\
offset=-0.02 \
  output.mp3
```

**특징:**
- 파일 후처리에 최적
- 정밀한 결과 (전체 오디오를 미리 분석)
- Linear 모드 사용 가능
- 처리 시간이 2배

---

## Dynamic vs Linear 모드

### Dynamic 모드

- `measured_*` 파라미터가 제공되지 않으면 자동으로 사용
- 실시간으로 게인을 조정하여 LRA를 타겟에 맞춤
- True Peak 감지를 위해 오디오를 **192 kHz로 업샘플링**
- 동적 범위가 압축될 수 있음

### Linear 모드

- `measured_*` 파라미터가 모두 제공되고 `linear=true`일 때 사용
- 전체 오디오에 **균일한 게인**을 적용 (동적 범위 보존)
- 원본의 다이나믹스를 최대한 유지

**Linear 모드에서 Dynamic으로 폴백되는 경우:**
1. 타겟 LRA가 소스 LRA보다 낮을 때
2. 게인 적용 후 True Peak가 타겟 TP를 초과할 때

```
                ┌─────────────────────┐
                │   measured_* 제공?   │
                └─────────┬───────────┘
                    yes   │   no
              ┌───────────┴───────────┐
              ▼                       ▼
        ┌───────────┐          ┌───────────┐
        │  Linear   │          │  Dynamic  │
        │   모드     │          │   모드     │
        └─────┬─────┘          └───────────┘
              │
        ┌─────┴─────────────────┐
        │ TP 초과 or LRA 불충분? │
        └─────┬─────────────────┘
          yes │   no
        ┌─────┴───┐  ┌──────────┐
        │ Dynamic │  │ Linear   │
        │ 폴백    │  │ 유지     │
        └─────────┘  └──────────┘
```

---

## 본 프로젝트에서의 사용

이 프로젝트는 Single-Pass Dynamic 모드를 사용한다. 구현은 `src/yt_chapter_extractor/audio.py`에 위치한다.

### 라우드니스 측정 (`measure_loudness`)

```python
# audio.py:95-124
cmd = [
    "ffmpeg",
    "-i", str(mp3_path),
    "-af", "loudnorm=print_format=json",
    "-f", "null",
    "-",
]
```

- `-af loudnorm=print_format=json`: 정규화는 수행하지 않고 측정 결과만 JSON으로 출력
- `-f null -`: 실제 출력 파일을 생성하지 않음 (측정 전용)
- stderr에서 JSON을 정규식으로 파싱하여 `input_i` (Integrated Loudness) 값 추출

### 라우드니스 정규화 (`normalize_audio`)

```python
# audio.py:127-159
cmd = [
    "ffmpeg",
    "-y",
    "-i", str(mp3_path),
    "-af", f"loudnorm=I={target_lufs}:LRA=11:TP=-1.5",
    "-codec:a", "libmp3lame",
    "-q:a", "2",
    str(tmp_path),
]
```

**적용된 파라미터:**

| 파라미터 | 값 | 설명 |
|----------|-----|------|
| `I` | 사용자 지정 | 타겟 Integrated Loudness (기본 -14 LUFS) |
| `LRA` | 11 | 타겟 Loudness Range. 음악에 적합한 중간 범위 |
| `TP` | -1.5 | True Peak 상한. 클리핑 방지에 충분한 여유 |

**안전한 파일 교체 전략:**

1. 같은 디렉토리에 임시 파일 생성 (`tempfile.mkstemp`)
2. ffmpeg으로 임시 파일에 정규화 결과 기록
3. `os.replace()`로 원본 파일을 원자적(atomic) 교체
4. 실패 시 임시 파일 정리 (try/except)

이 방식은 정규화 도중 실패해도 원본 파일이 손상되지 않는 것을 보장한다.

### 병렬 처리

측정과 정규화 모두 `ThreadPoolExecutor`와 `as_completed`를 사용하여 여러 파일을 병렬로 처리한다. ffmpeg 프로세스는 CPU 바운드이므로, 스레드 풀이 시스템 코어 수에 맞게 작업을 분배한다.

---

## 참고 자료

- [FFmpeg Filters Documentation - loudnorm](https://ffmpeg.org/ffmpeg-filters.html#loudnorm)
- [loudnorm - FFmpeg 7.1 Filter Docs](https://ayosec.github.io/ffmpeg-filters-docs/7.1/Filters/Audio/loudnorm.html)
- [Audio Loudness Normalization with FFmpeg](https://peterforgacs.github.io/2018/05/20/Audio-normalization-with-ffmpeg/)
- [EBU R128 Specification (PDF)](https://tech.ebu.ch/docs/r/r128.pdf)
- [EBU Loudness - Technology & Innovation](https://tech.ebu.ch/loudness)
