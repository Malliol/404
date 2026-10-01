# Курс «Подготовка к специалисту по платформе 1С»

Источник: YouTube-плейлист https://www.youtube.com/playlist?list=PLh28ogpgRJUPQDnx1uV9p19jLbpyBa3ua (129 уроков).

- `transcripts/` — полный текст каждого урока (автосубтитры YouTube `ru-orig`, очищены от таймкодов и дублей; возможны ошибки распознавания).
- `notes/` — конспект каждого урока по материалам расшифровки.
- `vtt2txt.py` — скрипт очистки субтитров.

Получение субтитров:

```
pip install yt-dlp
yt-dlp --skip-download --write-auto-subs --sub-langs ru-orig --sub-format vtt \
  -o "%(playlist_index)02d_%(id)s" "<playlist url>"
```
