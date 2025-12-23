# Smart Waste Monitoring Dashboard

Simple React/Next.js dashboard for visualizing trash bin fill levels.

## Features

- Real-time bin status display
- Auto-refresh every 5 seconds
- Color-coded fill levels (Green=Empty, Orange=Half, Red=Full)
- Statistics summary
- Responsive design with Tailwind CSS

## Setup

1. Install dependencies:
```bash
cd dashboard
npm install
```

2. Start development server:
```bash
npm run dev
```

3. Open browser:
```
http://localhost:3000
```

## Requirements

- Node.js 18+
- Backend API running on http://localhost:8000

## Build for Production

```bash
npm run build
npm start
```

## TODO

- Add filtering by fill level
- Add sorting options
- Add search functionality
- Add detailed bin view (modal with location map)
- Add historical data charts
- Add notifications for full bins
- Add video upload interface
- Add authentication
