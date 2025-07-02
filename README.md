# Label Generator

A modern web application for generating 4x6" thermal labels with customizable templates.

## Features

- **Template System**: Pre-configured templates for different use cases
- **Live Preview**: Real-time preview of labels before printing
- **Customizable Settings**: Font size, family, bold text, rows, columns
- **PDF Export**: Download labels as PDF for printing
- **Direct Printing**: Print directly from the browser
- **URL Parameters**: Share configurations via URL

## Templates

The application includes three built-in templates:

### Samples
- CSF 0.5mL (40 labels)
- PLASMA 0.5mL (15 labels)

### Autopsy
- SKELETAL MUSCLE 0.5mL (25 labels)
- LIVER 0.5mL (20 labels)
- HEART 0.5mL (15 labels)

### Cables
- PC (50 labels)

## Adding New Templates

To add a new template, edit the `templates.json` file:

```json
{
  "template_id": {
    "name": "Template Name",
    "description": "Template description",
    "items": [
      {"text": "Label text\n{{ today }}\nSample type", "quantity": 10}
    ],
    "defaults": {
      "font_size": 24,
      "bold": true,
      "rows": 10,
      "columns": 3,
      "font_family": "DejaVuSans"
    }
  }
}
```

## URL Parameters

The application supports URL parameters for sharing configurations:

- `template`: Template ID (e.g., `samples`, `autopsy`, `cables`)
- `font_size`: Font size (8-72)
- `bold`: Bold text (true/false)
- `rows`: Number of rows per sheet
- `columns`: Number of columns per sheet
- `font_family`: Font family

Example: `http://localhost:8777/?template=autopsy&font_size=20&bold=false`

## Running the Application

1. Install dependencies:
   ```bash
   pip install fastapi uvicorn pillow pytz
   ```

2. Run the server:
   ```bash
   python app.py
   ```

3. Open your browser to `http://localhost:8777`

## API Endpoints

- `GET /`: Main application interface
- `GET /api/templates`: Get all available templates
- `GET /api/templates/{template_id}`: Get specific template
- `POST /preview`: Generate preview images
- `POST /generate`: Generate PDF for download/printing 