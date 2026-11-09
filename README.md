<div align="center">
  <h1>🧩 Challenges Projects</h1>
  <h3>Hands-on Data &amp; AI Engineering Challenges</h3>

  <p>
    A collection of independent, safety-first prototypes built with modern Python tooling:
    <strong>FastAPI, Pydantic, local LLMs and OCR</strong>.
    Each challenge lives in its own folder with its own README, dependencies and tests.
  </p>

  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/API-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Validation-Pydantic%20v2-E92063?style=for-the-badge&logo=pydantic&logoColor=white" />
  <img src="https://img.shields.io/badge/Tests-Pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white" />
  <img src="https://img.shields.io/badge/Status-Experimental%20Prototypes-orange?style=for-the-badge" />
</div>

<br>

> ⚠️ **Disclaimer** — These projects are **experimental research prototypes**, not medical devices.
> They do not provide diagnosis, prescriptions, real stock/price data, or clinical advice.
> Do not use them for real medical or commercial decisions.

<hr>

## 📚 Challenges

| # | Challenge | Description | Stack | Code |
| :---: | :--- | :--- | :--- | :--- |
| 1 | **Pharmacy Patient Assistant API** | Turns multilingual pharmacy requests (French, Darija, Arabic, mixed) into strictly validated structured JSON. | FastAPI · Ollama · Llama 3.2 · Pydantic · Pytest | [challenge-1-pharmacy-assistant](challenge-1-pharmacy-assistant/) |
| 2 | **Mediscan — Medication Box Recognition** | Reads printed Arabic/French text from medication boxes with OCR and matches products against a local catalogue. | FastAPI · Tesseract (tesserocr) · Pillow · Pydantic · Pytest | [challenge-2-mediscan](challenge-2-mediscan/) |

<hr>

## 🗂️ Repository Layout

```text
Challenges_projects/
├── README.md                        # this index
├── .gitignore                       # shared ignores (venv, caches, .env)
├── challenge-1-pharmacy-assistant/  # LLM structured extraction microservice
└── challenge-2-mediscan/            # OCR + catalogue matching microservice
```

Each folder contains its own `README.md`, `requirements*.txt`, tests, documentation and run
instructions:

* [Challenge 1 — Pharmacy Patient Assistant API](challenge-1-pharmacy-assistant/README.md)
* [Challenge 2 — Mediscan Medication Box Recognition](challenge-2-mediscan/README.md)

<hr>

## 📨 Contact

[LinkedIn](https://www.linkedin.com/in/abderrahmane-chahiri-151b26237/) •
[Gmail](mailto:chahiri.abderrahmane.eng@gmail.com)

<div align="center">
  <sub>Built as experimental prototypes · Not approved for clinical or commercial use.</sub>
  <br><br>
  Made with ❤️ by <a href="https://www.linkedin.com/in/abderrahmane-chahiri-151b26237/">Abderrahmane Chahiri</a>
</div>
