# Tactical Meeting Assistant

עוזר פגישות AI בזמן אמת שמקשיב לשיחה ונותן עצות טקטיות בעברית.

## Features

- **Voice Diarization**: מזהה את הקול שלך ומבדיל בינך לבין משתתפים אחרים
- **Real-time Transcription**: תמלול בזמן אמת בעברית באמצעות Deepgram Nova-2
- **Tactical Advice**: עצות קצרות וחדות מבוססות על הבריף שהגדרת
- **Mobile Optimized**: עובד על טלפון ומחשב עם ויברציה להתראות

## Tech Stack

- **Backend**: FastAPI + WebSockets
- **Speech-to-Text**: Deepgram Nova-2 with Diarization
- **AI Advice**: OpenAI GPT-4o-mini
- **Frontend**: HTML5 + Tailwind CSS (RTL)

## Environment Variables

Set these in Railway:

```
OPENAI_API_KEY=sk-...
DEEPGRAM_API_KEY=...
```

## Usage

1. הזן את פרטי הפגישה (משתתפים, מטרה, אתגרים)
2. עבור כיול קולי (5 שניות של דיבור)
3. התחל את הפגישה והנח את הטלפון על השולחן
4. קבל עצות בזמן אמת!

## Deployment

### Railway (Recommended)
1. Connect this repo to Railway
2. Add environment variables
3. Deploy!

### Local Development
```bash
pip install -r requirements.txt
export OPENAI_API_KEY=your-key
export DEEPGRAM_API_KEY=your-key
uvicorn main:app --reload
```

## License

MIT
