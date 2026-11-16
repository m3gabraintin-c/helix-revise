# Helix Revise

A free, independent revision site, built as a single self-contained HTML page.

**Live site: https://m3gabraintin-c.github.io/helix-revise/** · Found a wrong answer? [Report it](https://github.com/m3gabraintin-c/helix-revise/issues/new).

## What's inside

Topic-by-topic practice quizzes for:

- **VCE Units 3 & 4:** Mathematical Methods, General Mathematics, Specialist Mathematics, Chemistry, Physics, Biology, Psychology
- **VCE Units 1 & 2:** Chemistry, Biology, Psychology, Mathematical Methods, Physics
- **GCSE (Edexcel, Triple Higher):** Biology

Each subject is split into topics and subtopics. You can quiz one subtopic at a time or use **Build a quiz** to mix several. Progress is stored only in your browser (`localStorage`). Nothing is sent to a server.

## Question files

`questions/` holds every question as Markdown, one folder per subject (`questions.md` + `answers.md`). It is generated from the `DATA` block in `index.html`, so after editing questions there, regenerate and check it:

```bash
python3 scripts/build_questions.py && python3 scripts/verify.py
```

## Running it

No build step and no dependencies. Open `index.html` in a browser, or serve the folder:

```bash
python3 -m http.server 8000
```

Then visit http://localhost:8000. Web fonts load from Google Fonts. Without a connection the page falls back to system fonts.

## Hosting

`index.html` sits at the repo root, so GitHub Pages works as is: **Settings → Pages → Deploy from a branch → `main` / root**.

## Accessibility

The site targets WCAG 2.1 AA: semantic headings, a skip link, full keyboard use with visible focus, focus moved to the new heading on every page change, AA colour contrast in light and dark themes, text (not just colour) for right and wrong answers, labelled form controls, and no animation when the system asks for reduced motion. Please report any barrier as an issue.

## Contributing

Corrections and new questions are welcome as [issues](https://github.com/m3gabraintin-c/helix-revise/issues) or pull requests. Edit questions in the `DATA` block of `index.html`, then regenerate `questions/` with the command above.

## Licence

- Code: [MIT](LICENSE)
- Questions and answers: [CC BY-NC 4.0](LICENSE-QUESTIONS.md)

## Disclaimer

Not affiliated with or endorsed by the VCAA, Pearson Edexcel or any other exam board or revision provider. Questions are original and were written for this site; some were drafted with AI help and then reviewed.
