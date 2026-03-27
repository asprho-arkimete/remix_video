# 🎬 Remix Video

**Remix video tramite Flux 2 — frame key by frame key — con Veo 3 e A2E.**
Crea la tua traccia video su una timeline dedicata: taglia clip, genera nuove sequenze ed estendi quelle esistenti, il tutto guidato da modelli di diffusione di ultima generazione.

---

## ✨ Features

- 🔑 **Frame key by frame key** — controllo preciso su ogni keyframe del video
- 🎞️ **Timeline interattiva** — visualizza, taglia e riorganizza le clip
- ✂️ **Taglia & Genera** — ritaglia sequenze esistenti o creane di nuove da zero
- 📐 **Estendi le clip** — prolunga qualsiasi clip con generazione AI coerente
- 🤖 **Flux 2 + Veo 3 + A2E** — pipeline basata sui modelli più avanzati
- 🎨 **LoRA support** — carica qualsiasi LoRA Flux 2 Klein 9B da CivitAI

---

## 🛠️ Installazione

### 1. Installa Anaconda e Python 3.10

Scarica e installa Anaconda:
👉 https://anaconda.org/channels/anaconda/packages/python/overview

Durante l'installazione seleziona **Python 3.10**.

istalla python 3.10 nel sistema operativo windows 32bit or 64bit: https://www.python.org/downloads/release/python-3100/

scarica,istalla cursor per edit code python:
https://cursor.com/get-started?utm_source=google_paid&utm_campaign=[Search]%20[Brand]%20[EN]%20[EMEA%20T1]%20[Broad]%20[Max%20Conv]%20[Subscribes]%20Brand&utm_term=cursor%20agent&utm_medium=paid&utm_content=799669577710&cc_platform=google&cc_campaignid=23633435220&cc_adgroupid=197790260567&cc_adid=799669577710&cc_keyword=cursor%20agent&cc_matchtype=b&cc_device=c&cc_network=g&cc_placement=&cc_location=1008736&cc_adposition=&gad_source=1&gad_campaignid=23633435220&gbraid=0AAAABAkdGgRhKPWnW22EPSKYaajJkUUEN&gclid=Cj0KCQjw1ZjOBhCmARIsADDuFTDd_ZFJNPCRyaAmhc_5pGbVkZK5GdeSZu0fbtfDGjQud3cuey1jcNgaApccEALw_wcB

---

### 2. Clona il repository

```bash
git clone https://github.com/asprho-arkimete/remix_video.git
cd remix_video
```

---

### 3. Crea e attiva il virtual environment

```bash
python3.10 -m venv vrmx
vrmx\Scripts\activate
```

> 💡 Su **macOS/Linux** usa: `source vrmx/bin/activate`

---

### 4. Installa le dipendenze

```bash
pip install -r requisiti.txt
```

---

### 5. Scarica una LoRA (opzionale ma consigliato)

Scegli e scarica una LoRA compatibile con **Flux 2 Klein 9B** da CivitAI:
👉 https://civitai.com/search/models?baseModel=Flux.2%20D&baseModel=Flux.2%20Klein%209B&baseModel=Flux.2%20Klein%209B-base&modelType=LORA&sortBy=models_v9

Inserisci il file `.safetensors` nella cartella `loras/` del progetto.

---

### 6. Avvia l'applicazione

```bash
python rmx.py
```

---

## 📋 Requisiti di sistema

| Componente | Minimo consigliato |
|---|---|
| GPU | NVIDIA con CUDA 12.8+ |
| VRAM | 12 GB+ |
| RAM | 16 GB+ |
| Python | 3.10 |
| OS | Windows 10/11, Linux |

---

## 📦 Stack tecnologico

- [Flux 2 Klein 9B](https://civitai.com) — modello di diffusione video
- [Diffusers](https://github.com/huggingface/diffusers) — pipeline HuggingFace
- [MoviePy](https://zulko.github.io/moviepy/) — editing video programmatico
- [OpenCV](https://opencv.org/) — elaborazione frame
- [PyTorch](https://pytorch.org/) — backend deep learning (CUDA 12.8)
- [Transformers](https://github.com/huggingface/transformers) — modelli language/vision
- [PEFT](https://github.com/huggingface/peft) — LoRA fine-tuning support

---

## 📄 Licenza

MIT License — libero per uso personale e commerciale.

---

> Made with ❤️ by [asprho-arkimete](https://github.com/asprho-arkimete)
