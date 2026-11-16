# Helix Revise

A free, independent revision site, built as a single self-contained HTML page.

## What's inside

Topic-by-topic practice quizzes for:

- **VCE Units 3 & 4:** Mathematical Methods, General Mathematics, Specialist Mathematics, Chemistry, Physics, Biology, Psychology
- **VCE Units 1 & 2:** Chemistry, Biology, Psychology, Mathematical Methods, Physics
- **GCSE (Edexcel, Triple Higher):** Biology

Each subject is split into topics and subtopics. You can quiz one subtopic at a time or use **Build a quiz** to mix several. Progress is stored only in your browser (`localStorage`). Nothing is sent to a server.

## Running it

No build step and no dependencies. Open `index.html` in a browser, or serve the folder:

```bash
python3 -m http.server 8000
```

Then visit http://localhost:8000. Web fonts load from Google Fonts. Without a connection the page falls back to system fonts.

## Hosting

`index.html` sits at the repo root, so GitHub Pages works as is: **Settings → Pages → Deploy from a branch → `main` / root**.

## Disclaimer

Not affiliated with or endorsed by the VCAA, Pearson Edexcel or any other exam board or revision provider. Questions are original and were written for this site.
