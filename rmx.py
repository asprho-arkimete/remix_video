# ── imports ────────────────────────────────────────────────────────────────────
import tkinter as tk
from tkinter import ttk, filedialog
import os
import shutil
import subprocess
import webbrowser
import gc

import torch
from PIL import Image, ImageTk
from moviepy import VideoFileClip
from tkinterdnd2 import TkinterDnD, DND_FILES
from diffusers import Flux2KleinPipeline
from optimum.quanto import freeze, qfloat8, quantize
from deep_translator import GoogleTranslator

# ── cartelle ───────────────────────────────────────────────────────────────────
for j in ['framekey', 'lora', 'video_clips']:
    os.makedirs(j, exist_ok=True)

# utility Lora:
# https://civitai.com/search/models?baseModel=Flux.2%20D&baseModel=Flux.2%20Klein%209B
# &baseModel=Flux.2%20Klein%209B-base&modelType=LORA&sortBy=models_v9

# ── finestra principale ────────────────────────────────────────────────────────
window = TkinterDnD.Tk()
window.title("remix Video")
window.geometry("1028x960")
window.config(bg='gray')
window.resizable(False, False)

clipdir = 'video_clips'
clip_selezionata = ''
os.makedirs(clipdir, exist_ok=True)

dim  = 512
dim2 = 128

current_photo_frame = None
current_photo_begin = None
current_photo_last  = None
current_photo       = None
photo               = None      # riferimento globale per flux2()

frame_dir = "framekey"
os.makedirs(frame_dir, exist_ok=True)

frames = []

# dizionario unico per tutti i path di riferimento
path_references = {
    'frame':       None,
    'frame_begin': None,
    'frame_last':  None
}

RESUME_FILE = "indice.txt"
TEMP_FILE   = "temp.mp4"

# ── drag & drop ────────────────────────────────────────────────────────────────
def drag_drop(event, canvas, dimensione, ref_key):
    global current_photo_frame, current_photo_begin, current_photo_last

    path = event.data.strip('{}')
    path_references[ref_key] = path
    print(f"Path salvato per '{ref_key}': {path}")

    try:
        img = Image.open(path)
        w, h = img.size
        rw, rh = dimensione, dimensione
        if w >= h:
            rh = (rw * h) // w
        else:
            rw = (rh * w) // h

        img   = img.resize((rw, rh), Image.BICUBIC)
        photo_tmp = ImageTk.PhotoImage(img)

        if canvas == frame:
            current_photo_frame = photo_tmp
        elif canvas == frame_begin:
            current_photo_begin = photo_tmp
        elif canvas == frame_last:
            current_photo_last  = photo_tmp

        canvas.delete('all')
        canvas.create_image(dimensione // 2, dimensione // 2,
                            image=photo_tmp, anchor='center')

    except Exception as e:
        print(f"Errore drag & drop: {e}")


# ── canvas immagine principale ─────────────────────────────────────────────────
frame = tk.Canvas(window, width=dim, height=dim, bg='red')
frame.grid(row=0, column=0)
frame.create_text(dim // 2, dim // 2, text="Image 1", fill='white')
frame.drop_target_register(DND_FILES)
frame.dnd_bind('<<Drop>>', lambda e: drag_drop(e, frame, dim, 'frame'))

# ── pannello strumenti destra ──────────────────────────────────────────────────
frame_strumenti = tk.Frame(window, bg='gray')
frame_strumenti.grid(row=0, column=1, sticky='n', padx=5, pady=5)

# ── raccoglitore clip con scrollbar ───────────────────────────────────────────
frame_raccoglitoreclips = tk.Frame(window, bg='gray')
frame_raccoglitoreclips.grid(row=1, column=0, columnspan=4,
                              sticky='w', padx=5, pady=5)

canvas_scroll = tk.Canvas(frame_raccoglitoreclips, bg='gray', width=800, height=150)
scrollbar = tk.Scrollbar(frame_raccoglitoreclips, orient='horizontal',
                         command=canvas_scroll.xview)
canvas_scroll.configure(xscrollcommand=scrollbar.set)
scrollbar.pack(side='bottom', fill='x')
canvas_scroll.pack(side='top', fill='x')

inner_frame = tk.Frame(canvas_scroll, bg='gray')
canvas_scroll.create_window((0, 0), window=inner_frame, anchor='nw')

thumbnail_refs  = []
bordo_canvases  = []


def seleziona_clip(canvas_bordo, nome_clip):
    global clip_selezionata
    for c in bordo_canvases:
        c.config(bg='#00fcff')
    canvas_bordo.config(bg='lightgreen')
    clip_selezionata = nome_clip
    elimina_clip.config(text=f'Elimina: {nome_clip}')
    carica_frames()


def aggiorna_lista_clips():
    global thumbnail_refs, bordo_canvases

    for widget in inner_frame.winfo_children():
        widget.destroy()
    thumbnail_refs.clear()
    bordo_canvases.clear()

    for i, clip_name in enumerate(sorted(os.listdir(clipdir))):
        if not clip_name.endswith(('.mp4', '.avi', '.mov', '.mkv')):
            continue

        clip_path = os.path.join(clipdir, clip_name)

        canvas_bordo = tk.Canvas(inner_frame, width=dim2 + 6, height=dim2 + 6,
                                  bg='#00fcff', highlightthickness=0)
        canvas_bordo.grid(row=0, column=i, padx=3, pady=3)
        bordo_canvases.append(canvas_bordo)

        canvas_thumb = tk.Canvas(canvas_bordo, width=dim2, height=dim2,
                                  bg='gray', highlightthickness=0)
        canvas_bordo.create_window(3, 3, window=canvas_thumb, anchor='nw')

        tk.Label(inner_frame, text=clip_name, bg='gray', fg='white',
                 wraplength=dim2).grid(row=1, column=i)

        canvas_bordo.bind('<Button-1>',
            lambda e, cb=canvas_bordo, n=clip_name: seleziona_clip(cb, n))
        canvas_thumb.bind('<Button-1>',
            lambda e, cb=canvas_bordo, n=clip_name: seleziona_clip(cb, n))

        try:
            clip    = VideoFileClip(clip_path)
            frame_0 = clip.get_frame(0)
            clip.close()

            img  = Image.fromarray(frame_0)
            w, h = img.size
            if w >= h:
                rw, rh = dim2, (dim2 * h) // w
            else:
                rw, rh = (dim2 * w) // h, dim2

            img   = img.resize((rw, rh), Image.BICUBIC)
            photo_tmp = ImageTk.PhotoImage(img)
            thumbnail_refs.append(photo_tmp)
            canvas_thumb.create_image(dim2 // 2, dim2 // 2,
                                      image=photo_tmp, anchor='center')

        except Exception as e:
            print(f"Errore con {clip_name}: {e}")

    inner_frame.update_idletasks()
    canvas_scroll.configure(scrollregion=canvas_scroll.bbox('all'))


def f_aggiungi():
    global clip_selezionata

    path = filedialog.askopenfilename(
        title="Seleziona video",
        filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv"), ("All files", "*.*")]
    )
    if not path:
        return

    clips        = sorted([c for c in os.listdir(clipdir) if c.endswith('.mp4')])
    numero_clip  = len(clips)

    if clip_selezionata == '':
        nuovo_nome = os.path.join(clipdir, f"clip_{numero_clip}.mp4")
        shutil.copyfile(path, nuovo_nome)
    else:
        os.makedirs(os.path.join(clipdir, "temp"), exist_ok=True)
        indice = int(clip_selezionata.replace("clip_", "").replace(".mp4", ""))

        for k in range(numero_clip - 1, indice, -1):
            src = os.path.join(clipdir, f"clip_{k}.mp4")
            dst = os.path.join(clipdir, "temp", f"clip_{k+1}.mp4")
            shutil.copyfile(src, dst)

        shutil.copyfile(path, os.path.join(clipdir, f"clip_{indice+1}.mp4"))

        for k in range(indice + 2, numero_clip + 1):
            src = os.path.join(clipdir, "temp", f"clip_{k}.mp4")
            dst = os.path.join(clipdir, f"clip_{k}.mp4")
            shutil.move(src, dst)

        shutil.rmtree(os.path.join(clipdir, "temp"))

    aggiorna_lista_clips()


aggiungi = tk.Button(frame_strumenti, text='Aggiungi Video', command=f_aggiungi)
aggiungi.grid(row=0, column=0, sticky='n')


# ── f_estrai_frame  (Dividi clip / Begin frame) ────────────────────────────────
def f_estrai_frame():
    global frames, current_photo_begin, clip_selezionata

    if not frames or not clip_selezionata:
        print("[ERRORE] Nessun frame o clip selezionata")
        return

    idx = int(scrool_frames.get())
    idx = max(0, min(idx, len(frames) - 1))

    img       = Image.fromarray(frames[idx])
    nome_base = os.path.splitext(clip_selezionata)[0]
    nome_foto = f"{nome_base}_{idx}.jpg"
    img.save(os.path.join(frame_dir, nome_foto))
    print(f"Frame salvato: {nome_foto}")

    # thumbnail
    w, h = img.size
    dim2_t = 200
    if w >= h:
        rw, rh = dim2_t, (dim2_t * h) // w
    else:
        rw, rh = (dim2_t * w) // h, dim2_t
    img_small           = img.resize((rw, rh), Image.Resampling.LANCZOS)
    current_photo_begin = ImageTk.PhotoImage(img_small)
    frame_begin.delete('all')
    frame_begin.create_image(dim2_t // 2, dim2_t // 2, image=current_photo_begin)

    # divisione clip
    indice_corrente = int(nome_base.replace('clip_', ''))
    clip_path       = os.path.join(clipdir, clip_selezionata)
    temp_dir        = os.path.join(clipdir, "temp")

    forza_taglio_minimo = (idx == 0)

    try:
        video           = VideoFileClip(clip_path)
        fps             = video.fps
        durata_totale   = video.duration
        n_frames_totali = int(durata_totale * fps)

        if idx >= n_frames_totali - 1:
            print("[INFO] Frame finale: solo jpg, nessuna divisione.")
            video.close()
            return

        taglio = (1 / fps) if forza_taglio_minimo else (idx / fps)
        if taglio >= durata_totale - (1 / fps):
            taglio = durata_totale - 0.1

        print(f"[OK] Taglio a {taglio:.3f}s su {durata_totale:.3f}s (FPS: {fps})")

        parte1 = video.subclipped(0, taglio)
        parte2 = video.subclipped(taglio, max(0, durata_totale - 0.01))

        os.makedirs(temp_dir, exist_ok=True)
        clips_in_dir     = sorted([c for c in os.listdir(clipdir)
                                    if c.startswith('clip_') and c.endswith('.mp4')])
        indici_esistenti = sorted([int(c.replace('clip_', '').replace('.mp4', ''))
                                    for c in clips_in_dir])
        ultimo_indice    = indici_esistenti[-1] if indici_esistenti else indice_corrente

        for k in range(indice_corrente + 1, ultimo_indice + 1):
            src = os.path.join(clipdir, f"clip_{k}.mp4")
            if os.path.exists(src):
                shutil.move(src, os.path.join(temp_dir, f"clip_{k+1}.mp4"))

        p1_path = os.path.join(clipdir, "temp_p1.mp4")
        p2_path = os.path.join(clipdir, "temp_p2.mp4")

        print("[...] Scrittura parti...")
        parte1.write_videofile(p1_path, logger=None, codec="libx264", audio_codec="aac")
        parte2.write_videofile(p2_path, logger=None, codec="libx264", audio_codec="aac")

        parte1.close()
        parte2.close()
        video.close()

        os.replace(p1_path, os.path.join(clipdir, f"clip_{indice_corrente}.mp4"))
        os.replace(p2_path, os.path.join(clipdir, f"clip_{indice_corrente+1}.mp4"))

        for k in range(indice_corrente + 2, ultimo_indice + 2):
            src = os.path.join(temp_dir, f"clip_{k}.mp4")
            if os.path.exists(src):
                shutil.move(src, os.path.join(clipdir, f"clip_{k}.mp4"))

        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

        print("[FINITO] Clip divisa e indici aggiornati.")
        aggiorna_lista_clips()

    except Exception as e:
        print(f"[ERRORE] Durante il taglio: {e}")
        if 'video' in locals():
            video.close()


# ── canvas begin / last ────────────────────────────────────────────────────────
frame_begin = tk.Canvas(frame_strumenti, width=dim2, height=dim2, bg='blue')
frame_begin.grid(row=1, column=0, sticky='n')
frame_begin.create_text(dim2 // 2, dim2 // 2, text="Image 2", fill='white')
frame_begin.drop_target_register(DND_FILES)
frame_begin.dnd_bind('<<Drop>>', lambda e: drag_drop(e, frame_begin, dim2, 'frame_begin'))

frame_last = tk.Canvas(frame_strumenti, width=dim2, height=dim2, bg='magenta')
frame_last.grid(row=1, column=1, sticky='n')
frame_last.create_text(dim2 // 2, dim2 // 2, text="Image 3", fill='white')
frame_last.drop_target_register(DND_FILES)
frame_last.dnd_bind('<<Drop>>', lambda e: drag_drop(e, frame_last, dim2, 'frame_last'))


# ── f_estrai_ultimo_frame_taglia_porzione_precedente  (Begin → taglia prima) ───
# FIX: except Exception, current_photo_last, os.replace(), aggiorna_lista_clips()
def f_estrai_ultimo_frame_taglia_porzione_precedente():
    global frames, current_photo_last, clip_selezionata

    if not frames or not clip_selezionata:
        print("[ERRORE] Nessun frame o clip selezionata")
        return

    idx = int(scrool_frames.get())
    idx = max(0, min(idx, len(frames) - 1))

    img       = Image.fromarray(frames[idx])
    nome_base = os.path.splitext(clip_selezionata)[0]
    nome_foto = f"{nome_base}_{idx}.jpg"
    img.save(os.path.join(frame_dir, nome_foto))
    print(f"Frame salvato: {nome_foto}")

    # thumbnail → frame_last  (FIX: variabile corretta)
    w, h = img.size
    dim2_t = 200
    if w >= h:
        rw, rh = dim2_t, (dim2_t * h) // w
    else:
        rw, rh = (dim2_t * w) // h, dim2_t
    img_small          = img.resize((rw, rh), Image.Resampling.LANCZOS)
    current_photo_last = ImageTk.PhotoImage(img_small)   # FIX
    frame_last.delete('all')
    frame_last.create_image(dim2_t // 2, dim2_t // 2, image=current_photo_last)

    # taglia: mantieni dal frame selezionato in poi
    indice_corrente = int(nome_base.replace('clip_', ''))
    clip_path       = os.path.join(clipdir, clip_selezionata)

    try:
        video           = VideoFileClip(clip_path)
        fps             = video.fps
        durata_totale   = video.duration
        n_frames_totali = int(durata_totale * fps)

        if idx == 0:
            print("[INFO] Frame 0: nessun taglio, clip invariata.")
            video.close()
            return

        if idx >= n_frames_totali - 1:
            print("[INFO] Frame finale: nessun taglio.")
            video.close()
            return

        taglio = min(idx / fps, durata_totale - 0.01)
        print(f"[OK] Taglio a {taglio:.3f}s su {durata_totale:.3f}s (FPS: {fps})")

        parte_finale = video.subclipped(taglio, max(0, durata_totale - 0.01))

        p1_path = os.path.join(clipdir, "temp_p1.mp4")
        print("[...] Scrittura parte finale...")
        parte_finale.write_videofile(p1_path, logger=None,
                                     codec="libx264", audio_codec="aac")

        parte_finale.close()
        video.close()

        # FIX: sostituzione file originale
        os.replace(p1_path, os.path.join(clipdir, f"clip_{indice_corrente}.mp4"))

        print("[FINITO] Clip tagliata dal frame selezionato in poi.")
        aggiorna_lista_clips()   # FIX

    except Exception as e:      # FIX: Exception maiuscolo
        print(f"[ERRORE] Durante il taglio: {e}")
        if 'video' in locals():
            video.close()


dividi_BF = tk.Button(frame_strumenti, text='Dividi clip\nBegin frame',
                       command=f_estrai_frame)
dividi_BF.grid(row=2, column=0, sticky='n')


# ── f_estrai_ultimo_frame_taglia  (Last frame → taglia dopo) ──────────────────
def f_estrai_ultimo_frame_taglia():
    global frames, current_photo_last, clip_selezionata

    if not frames or not clip_selezionata:
        print("[ERRORE] Nessun frame o clip selezionata")
        return

    idx = int(scrool_frames.get())
    idx = max(0, min(idx, len(frames) - 1))

    img       = Image.fromarray(frames[idx])
    nome_base = os.path.splitext(clip_selezionata)[0]
    nome_foto = f"{nome_base}_last_{idx}.jpg"
    img.save(os.path.join(frame_dir, nome_foto))
    print(f"Frame salvato: {nome_foto}")

    w, h = img.size
    if w >= h:
        rw, rh = dim2, (dim2 * h) // w
    else:
        rw, rh = (dim2 * w) // h, dim2
    img_small          = img.resize((rw, rh), Image.Resampling.LANCZOS)
    current_photo_last = ImageTk.PhotoImage(img_small)
    frame_last.delete('all')
    frame_last.create_image(dim2 // 2, dim2 // 2,
                             image=current_photo_last, anchor='center')

    indice_corrente = int(nome_base.replace('clip_', ''))
    clip_path       = os.path.join(clipdir, clip_selezionata)

    try:
        video           = VideoFileClip(clip_path)
        fps             = video.fps
        durata_totale   = video.duration
        n_frames_totali = int(durata_totale * fps)

        if idx == 0:
            print("[INFO] Frame 0: nessun taglio, clip invariata.")
            video.close()
            return

        taglio = min(idx / fps, durata_totale - 0.01)
        print(f"[OK] Taglio a {taglio:.3f}s su {durata_totale:.3f}s (FPS: {fps})")

        parte = video.subclipped(taglio, max(0, durata_totale - 0.01))

        p_path = os.path.join(clipdir, "temp_last.mp4")
        print("[...] Scrittura parte tagliata...")
        parte.write_videofile(p_path, logger=None, codec="libx264", audio_codec="aac")

        parte.close()
        video.close()

        os.replace(p_path, os.path.join(clipdir, f"clip_{indice_corrente}.mp4"))

        print("[FINITO] Clip tagliata al frame selezionato.")
        aggiorna_lista_clips()

    except Exception as e:
        print(f"[ERRORE] Durante il taglio: {e}")
        if 'video' in locals():
            video.close()


last_frame_btn = tk.Button(frame_strumenti, text='Taglia clip\nLast frame',
                            command=f_estrai_ultimo_frame_taglia)
last_frame_btn.grid(row=2, column=1, sticky='n')


# ── clear ──────────────────────────────────────────────────────────────────────
def clear():
    global frame, frame_begin, frame_last, path_references

    frame.delete('all')
    frame_begin.delete('all')
    frame_last.delete('all')

    frame.create_text(dim  // 2, dim  // 2, text="Image 1", fill='white', tags='label')
    frame_begin.create_text(dim2 // 2, dim2 // 2, text="Image 2", fill='white', tags='label')
    frame_last.create_text( dim2 // 2, dim2 // 2, text="Image 3", fill='white', tags='label')

    for key in path_references:
        path_references[key] = None


clear_photo_reference = tk.Button(frame_strumenti, text='Clear Reference', command=clear)
clear_photo_reference.grid(row=3, column=0, padx=5, pady=5)


# ── quick links ────────────────────────────────────────────────────────────────
siti = {
    "Grok Assistant":       "https://grok.com/",
    "Flow IA - Veo 3 Free": "https://labs.google/flow/about",
    "Creati.Studio - Veo 3":"https://www.creati.studio/workspace/home",
    "A2E - Veo NSFW Free":  "https://video.a2e.ai/image-to-video",
    "Email Temporanea":     "https://temp-mail.io/it"
}


def apri_sito():
    nome = combo_siti.get()
    if nome in siti:
        webbrowser.open(siti[nome])


combo_siti = ttk.Combobox(frame_strumenti, values=list(siti.keys()),
                           state='readonly', width=22)
combo_siti.set("Seleziona sito...")
combo_siti.grid(row=4, column=0, padx=5, pady=2)

btn_apri = tk.Button(frame_strumenti, text="Apri", command=apri_sito)
btn_apri.grid(row=5, column=0, padx=5, pady=2)


# ── elimina clip ───────────────────────────────────────────────────────────────
def f_eliminaclip():
    global clip_selezionata
    path = os.path.join(clipdir, clip_selezionata)
    if os.path.exists(path):
        try:
            os.remove(path)
            elimina_clip.config(text='Elimina clip')
            aggiorna_lista_clips()
            clip_selezionata = ''
        except Exception as e:
            print(f"Error: {e}")
    else:
        print(f"non esiste: {clip_selezionata}")


elimina_clip = tk.Button(frame_strumenti, text='Elimina clip', command=f_eliminaclip)
elimina_clip.grid(row=6, column=0, padx=5, pady=2)

aggiorna_lista_clips()

# ── label frame + slider ───────────────────────────────────────────────────────
lab_frame = tk.Label(window, text='Frame: 0')   # FIX: una sola dichiarazione
lab_frame.grid(row=2, column=0, sticky='w', padx=2, pady=2)


def carica_frames():
    global frames

    if not clip_selezionata:
        return

    video  = VideoFileClip(os.path.join(clipdir, clip_selezionata))
    frames = list(video.iter_frames())
    video.close()

    scrool_frames.config(to=len(frames) - 1)
    scrool_frames.set(0)
    update_lab()


def f_frames(val=None):
    global current_photo

    if not frames:
        return

    idx = int(scrool_frames.get())
    idx = max(0, min(idx, len(frames) - 1))

    img  = Image.fromarray(frames[idx])
    w, h = img.size

    if w >= h:
        rw, rh = dim, (dim * h) // w
    else:
        rw, rh = (dim * w) // h, dim

    img           = img.resize((rw, rh), Image.BICUBIC)
    current_photo = ImageTk.PhotoImage(img)

    frame.delete('all')
    frame.create_image(dim // 2, dim // 2, image=current_photo, anchor='center')


def update_lab(val=None):
    lab_frame.config(text=f"Frame: {int(scrool_frames.get())}")
    f_frames()


scrool_frames = ttk.Scale(window, from_=0, to=2000, length=500, command=update_lab)
scrool_frames.grid(row=3, column=0, sticky='w', padx=10, pady=5)

# ── pannello strumenti 2 ───────────────────────────────────────────────────────
frame_strumenti2 = tk.Frame(window, bg='gray')
frame_strumenti2.grid(row=4, column=0, sticky='w', padx=2, pady=10)

# FIX: blocco NON duplicato — una sola copia
text = tk.Text(frame_strumenti2, width=70, height=6)
text.grid(row=0, column=0, columnspan=5, pady=5)

tk.Label(frame_strumenti2, text='Steps', bg='gray', fg='white').grid(row=1, column=0)
tk.Label(frame_strumenti2, text='Lora 1', bg='gray', fg='white').grid(row=1, column=1)
tk.Label(frame_strumenti2, text='Lora 2', bg='gray', fg='white').grid(row=1, column=2)

steps_var     = tk.IntVar(value=25)
spinbox_steps = tk.Spinbox(frame_strumenti2, from_=1, to=50,
                            textvariable=steps_var, width=6)
spinbox_steps.grid(row=2, column=0, padx=5, pady=5, sticky='w')

combo_lora1 = ttk.Combobox(frame_strumenti2, values=[], width=15)
combo_lora1.grid(row=2, column=1, padx=5, pady=5, sticky='w')
combo_lora1.set("no_lora")

combo_lora2 = ttk.Combobox(frame_strumenti2, values=[], width=15)
combo_lora2.grid(row=2, column=2, padx=5, pady=5, sticky='w')
combo_lora2.set("no_lora")


# ── flux2 ──────────────────────────────────────────────────────────────────────
from lycoris import create_lycoris_from_weights
# FIX: global photo dichiarato correttamente
def flux2():
    global path_references, steps_var, current_photo, photo

    dtype = torch.bfloat16

    gc.collect()
    torch.cuda.empty_cache()
    torch.cuda.synchronize()
    print(f"[VRAM] Libera prima del caricamento: "
          f"{torch.cuda.mem_get_info()[0] / 1024**3:.2f} GB")

    print("Caricamento pipeline FLUX.2 klein 9B...")
    pipe = Flux2KleinPipeline.from_pretrained(
        "black-forest-labs/FLUX.2-klein-9B",
        torch_dtype=dtype,
        low_cpu_mem_usage=False
    )

    if hasattr(pipe, 'safety_checker'):
        pipe.safety_checker = None

    # ── utility: rileva se il safetensors è formato LoKr/LyCORIS ──────────────
    def is_lokr_lora(path: str) -> bool:
        """Restituisce True se il file contiene chiavi LoKr (lokr_w1/lokr_w2)."""
        try:
            from safetensors import safe_open
            with safe_open(path, framework="pt", device="cpu") as f:
                keys = list(f.keys())
            return any("lokr_w" in k for k in keys)
        except Exception:
            # fallback: prova con torch
            try:
                import torch as _torch
                sd = _torch.load(path, map_location="cpu", weights_only=True)
                return any("lokr_w" in k for k in sd.keys())
            except Exception:
                return False

    # ── caricamento LoRA con supporto Standard + LoKr/LyCORIS ────────────────
    def load_lora(pipe, lora_path: str, adapter_name: str, weight: float = 1.0):
        """
        Tenta prima il caricamento standard Diffusers.
        Se il formato è LoKr/LyCORIS usa lycoris-lora come fallback.
        Ritorna True se caricata con successo.
        """
        if is_lokr_lora(lora_path):
            print(f"  → Formato LoKr rilevato, uso LyCORIS per '{adapter_name}'")
            try:
                
                wrapper, _ = create_lycoris_from_weights(
                    weight, lora_path, pipe.transformer
                )
                wrapper.merge_to()
                print(f"  → LoKr/LyCORIS merged nel transformer ✓")
                return "lycoris"   # LyCORIS fa merge diretto, non serve set_adapters
            except ImportError:
                print("  ✗ lycoris-lora non installata! Esegui: pip install lycoris-lora")
                return False
            except Exception as e:
                print(f"  ✗ Errore LyCORIS: {e}")
                return False
        else:
            print(f"  → Formato standard LoRA, uso Diffusers per '{adapter_name}'")
            try:
                pipe.load_lora_weights(lora_path, adapter_name=adapter_name)
                print(f"  → LoRA standard caricata ✓")
                return "diffusers"
            except Exception as e:
                print(f"  ✗ Errore Diffusers load_lora_weights: {e}")
                return False

    # ── carica LoRA 1 e LoRA 2 ───────────────────────────────────────────────
    lora1_name      = combo_lora1.get()
    lora2_name      = combo_lora2.get()
    adapter_names   = []
    adapter_weights = []

    if lora1_name != 'no_lora':
        lora1_path = os.path.join("./lora", lora1_name)
        if os.path.exists(lora1_path):
            print(f"Caricamento LoRA 1: {lora1_name}")
            result = load_lora(pipe, lora1_path, "lora1", weight=1.0)
            if result == "diffusers":
                adapter_names.append("lora1")
                adapter_weights.append(1.0)
            elif result == "lycoris":
                print("  (LoKr già merged, non serve set_adapters)")
        else:
            print(f"  ✗ File non trovato: {lora1_path}")

    if lora2_name != 'no_lora':
        lora2_path = os.path.join("./lora", lora2_name)
        if os.path.exists(lora2_path):
            print(f"Caricamento LoRA 2: {lora2_name}")
            result = load_lora(pipe, lora2_path, "lora2", weight=1.0)
            if result == "diffusers":
                adapter_names.append("lora2")
                adapter_weights.append(1.0)
            elif result == "lycoris":
                print("  (LoKr già merged, non serve set_adapters)")
        else:
            print(f"  ✗ File non trovato: {lora2_path}")

    # ── set_adapters solo per le LoRA standard Diffusers ─────────────────────
    if adapter_names:
        if len(adapter_names) == 1:
            pipe.set_adapters(adapter_names[0], adapter_weights=adapter_weights[0])
        else:
            pipe.set_adapters(adapter_names, adapter_weights=adapter_weights)
        print(f"Adapter attivi: {adapter_names}")

    print("Quantizzazione transformer...")
    quantize(pipe.transformer, weights=qfloat8)
    freeze(pipe.transformer)

    print("Quantizzazione text encoder...")
    if hasattr(pipe, 'text_encoder') and pipe.text_encoder is not None:
        quantize(pipe.text_encoder, weights=qfloat8)
        freeze(pipe.text_encoder)

    print("Ottimizzazioni memoria...")
    pipe.enable_model_cpu_offload()
    pipe.enable_attention_slicing()
    pipe.vae.enable_slicing()
    pipe.vae.enable_tiling()

    gc.collect()
    torch.cuda.empty_cache()
    print(f"[VRAM] Dopo ottimizzazioni: "
          f"{torch.cuda.mem_get_info()[0] / 1024**3:.2f} GB")

    # prompt
    prompt = text.get("1.0", tk.END).strip()
    if not prompt:
        prompt = "a beautiful portrait, photorealistic, high detail"

    try:
        prompt_en = GoogleTranslator(source='it', target='en').translate(prompt)
        print(f"Prompt ITA: {prompt}\nPrompt ENG: {prompt_en}")
    except Exception as e:
        print(f"Traduzione non disponibile, uso originale: {e}")
        prompt_en = prompt

    # immagini di riferimento
    REF_SIZE = 512
    images   = []
    for key in ('frame', 'frame_begin', 'frame_last'):
        p = path_references.get(key)
        if p and os.path.exists(p):
            img_ref  = Image.open(p).convert("RGB")
            w, h     = img_ref.size
            if w >= h:
                rw, rh = REF_SIZE, (REF_SIZE * h) // w
            else:
                rw, rh = (REF_SIZE * w) // h, REF_SIZE
            img_ref = img_ref.resize((rw, rh), Image.BICUBIC)
            images.append(img_ref)
            print(f"Immagine riferimento: {key} → {rw}x{rh}")

    num_steps  = steps_var.get()
    print(f"Steps: {num_steps}")

    gen_params = {
        "prompt":             prompt_en,
        "height":             1024,
        "width":              1024,
        "guidance_scale":     1.0,
        "num_inference_steps": num_steps,
        "generator":          torch.Generator(device="cpu").manual_seed(0)
    }

    if len(images) == 1:
        gen_params["image"] = images[0]
    elif len(images) > 1:
        gen_params["image"] = images

    print("Generazione...")
    image = pipe(**gen_params).images[0]

    os.makedirs(frame_dir, exist_ok=True)
    pathout = os.path.join(frame_dir, "flux2_klein.png")
    k = 1
    while os.path.exists(pathout):
        pathout = os.path.join(frame_dir, f"flux2_klein_{k}.png")
        k += 1

    image.save(pathout)
    print(f"[OK] Immagine salvata: {pathout}")

    try:
        output_img = image.resize((dim, dim), Image.BICUBIC)
        photo = ImageTk.PhotoImage(output_img)   # FIX: global → non GC'd
        frame.delete("all")
        frame.create_image(dim // 2, dim // 2, image=photo, anchor='center')
        frame.update()
    except Exception as e:
        print(f"Errore visualizzazione: {e}")

    del pipe
    gc.collect()
    torch.cuda.empty_cache()
    torch.cuda.synchronize()
    print(f"[VRAM] Libera dopo scaricamento: "
          f"{torch.cuda.mem_get_info()[0] / 1024**3:.2f} GB")


button_flux2 = tk.Button(frame_strumenti2, text='Genera Image', command=flux2)
button_flux2.grid(row=2, column=3, padx=5, pady=5, sticky='w')


def load_lora():
    os.makedirs("./lora", exist_ok=True)
    models = [os.path.basename(l) for l in os.listdir("./lora")]
    combo_lora1['values'] = ["no_lora"] + models
    combo_lora2['values'] = ["no_lora"] + models


load_lora()

# ── rendering ──────────────────────────────────────────────────────────────────
def salva_indice(clipdir, indice):
    with open(os.path.join(clipdir, RESUME_FILE), 'w') as f:
        f.write(str(indice))


def leggi_indice(clipdir):
    with open(os.path.join(clipdir, RESUME_FILE), 'r') as f:
        return int(f.read().strip())


def ffmpeg_concat_due(clip_a, clip_b, output):
    list_file = output + "_list.txt"
    with open(list_file, 'w') as f:
        f.write(f"file '{os.path.abspath(clip_a).replace(chr(92), '/')}'\n")
        f.write(f"file '{os.path.abspath(clip_b).replace(chr(92), '/')}'\n")

    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
         "-i", list_file, "-c", "copy", output],
        check=True, capture_output=True
    )
    os.remove(list_file)


def f_rendering():
    global clipdir

    clips_paths = sorted(
        [os.path.join(clipdir, c)
         for c in os.listdir(clipdir)
         if 'clip_' in os.path.basename(c) and c.endswith('.mp4')],
        key=lambda x: int(os.path.basename(x).split('_')[1].split('.')[0])
    )

    numero_clips = len(clips_paths)
    if numero_clips == 0:
        print("Nessuna clip trovata in:", clipdir)
        return

    temp_path = os.path.join(clipdir, TEMP_FILE)

    if os.path.exists(temp_path):
        indice = leggi_indice(clipdir)
        print(f"▶ Resume: temp.mp4 trovato, riparto da clip {indice}")
    else:
        print("▶ Nuovo rendering: concateno clip 0 e clip 1")
        ffmpeg_concat_due(clips_paths[0], clips_paths[1], temp_path)
        indice = 2
        salva_indice(clipdir, indice)
        print(f"  ✓ temp.mp4 creato, indice salvato: {indice}")

    while indice < numero_clips:
        print(f"  ➕ Aggiungo clip {indice}/{numero_clips - 1}: "
              f"{os.path.basename(clips_paths[indice])}")

        temp_nuovo = temp_path + ".new.mp4"
        ffmpeg_concat_due(temp_path, clips_paths[indice], temp_nuovo)
        os.replace(temp_nuovo, temp_path)

        indice += 1
        salva_indice(clipdir, indice)
        print(f"  ✓ Checkpoint salvato, indice: {indice}")

    output_finale = "./video_finale.mp4"
    os.replace(temp_path, output_finale)
    os.remove(os.path.join(clipdir, RESUME_FILE))
    print(f"✅ Completato → {output_finale}")


button_rendering = tk.Button(
    frame_strumenti2,
    text="Rendering Video",
    bg='green', fg='white',
    font=("Arial", 10, "bold"),
    command=f_rendering
)
button_rendering.grid(row=2, column=4, padx=5, pady=5, sticky='w')

# ── mainloop ───────────────────────────────────────────────────────────────────
window.mainloop()