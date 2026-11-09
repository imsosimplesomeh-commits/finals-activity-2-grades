# Finals Activity 2 - Grades Notification Console

A Python/Tkinter desktop app that loads student grade records from a text file and emails each student their result through the [Brevo](https://www.brevo.com/) transactional email API.

Three themed variants share the same idea:

| File | Theme | Grades file |
|------|-------|-------------|
| `app.py` | Teal / Lobotomy-style console | `lobcorp_grades.txt` |
| `appGradeManager.py` | Crimson / Limbus-style console | `limbus_grades.txt` |
| `appGrades.py` | Navy and brass / Ruina-style console | `ruina_grades.txt` |

`brevo_client.py` holds the shared `send_brevo_email()` helper.

## Requirements

- Python 3.10+
- `tkinter` (bundled with the standard Python installer)
- `requests`, `python-dotenv`

```
pip install requests python-dotenv
```

## Setup

1. Create a free Brevo account and an API key.
2. Copy `.env.example` to `.env` and fill in your own values:

```
BREVO_API_KEY=...
SENDER_EMAIL=...   # a sender verified in Brevo
SENDER_NAME=...
```

`.env` is git-ignored. Never commit real keys.

## Run

```
python app.py
python appGradeManager.py
python appGrades.py
```

Without a valid `.env`, the app still opens, but sending an email shows an error.

## Notes

Student school project. Grade files contain sample/class data used for the activity.
