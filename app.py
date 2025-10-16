from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image, ImageDraw, ImageFont
import io
import math
from typing import List, Dict, Any
from pathlib import Path
import uvicorn
from datetime import datetime
import pytz
import json

app = FastAPI(title="Label Generator", description="A modern label generator web app")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure directories exist
templates_dir = Path("templates")
templates_dir.mkdir(exist_ok=True)
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# Load templates configuration
def load_templates() -> Dict[str, Any]:
    """Load templates from JSON file."""
    try:
        with open("templates.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("Warning: templates.json not found, using default templates")
        return {
            "samples": {
                "name": "Samples",
                "description": "CSF and Plasma samples",
                "items": [
                    {"text": "EXAMPLE TEXT\n{{ today }}\nCSF 0.5mL", "quantity": 40},
                    {"text": "EXAMPLE TEXT\n{{ today }}\nPLASMA 0.5mL", "quantity": 15},
                ],
                "defaults": {
                    "font_size": 24,
                    "bold": true,
                    "rows": 10,
                    "columns": 3,
                    "font_family": "DejaVuSans",
                },
            }
        }


# Create a simple test image in static directory
test_img = Image.new("RGB", (100, 100), color="red")
test_img.save(static_dir / "test.png")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    tz = pytz.timezone("America/Los_Angeles")
    today = datetime.now(tz).strftime("%-m/%-d/%Y")

    # Get URL parameters for essential settings only
    template_id = request.query_params.get("template", "samples")
    font_size = request.query_params.get("font_size", "24")
    # Default bold to true if not specified in URL
    bold = (
        request.query_params.get("bold", "true").lower() == "true"
        if "bold" in request.query_params
        else True
    )
    rows = request.query_params.get("rows", "10")
    columns = request.query_params.get("columns", "3")
    font_family = request.query_params.get("font_family", "DejaVuSans")

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "today": today,
            "template_id": template_id,
            "initial_font_size": font_size,
            "initial_bold": bold,
            "initial_rows": rows,
            "initial_columns": columns,
            "initial_font_family": font_family,
        },
    )


class LabelRequest(BaseModel):
    label_data: str
    font_size: int = 24
    bold: bool = False
    rows: int = 10
    columns: int = 3
    font_family: str = "DejaVuSans"


@app.get("/api/templates", response_class=JSONResponse)
async def get_templates():
    """Get all available templates."""
    return load_templates()


@app.get("/api/templates/{template_id}", response_class=JSONResponse)
async def get_template(template_id: str):
    """Get a specific template by ID."""
    templates_data = load_templates()
    if template_id not in templates_data:
        raise HTTPException(status_code=404, detail="Template not found")
    return templates_data[template_id]


def parse_input(input_text: str, variables: Dict[str, str] = None) -> List[str]:
    """Parse input text into a list of labels."""
    try:
        items = json.loads(input_text)
        labels = []

        # Merge with provided variables
        all_vars = {}
        if variables:
            all_vars.update(variables)

        # Always include today's date if not provided
        if "date" not in all_vars:
            all_vars["date"] = datetime.now().strftime("%m/%d/%Y")

        for item in items:
            text = item["text"]
            quantity = min(int(item.get("quantity", 1)), 300)  # Limit quantity to 300

            # Replace all variables
            for var_name, var_value in all_vars.items():
                text = text.replace(f"{{{{ {var_name} }}}}", str(var_value))

            labels.extend([text] * quantity)
        return labels
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid input format: {str(e)}")


def create_label_sheets(
    labels: List[str],
    font_size: int = 24,
    bold: bool = True,
    rows: int = 10,
    columns: int = 3,
    font_family: str = "DejaVuSans",
) -> List[Image.Image]:
    print(f"Creating label sheets with font size: {font_size}")
    cols, rows = columns, rows
    # Calculate label dimensions for 4x6" sheet at 203 DPI
    sheet_width, sheet_height = 812, 1218  # 4x6 inches at 203 DPI

    # Calculate label dimensions
    label_width = sheet_width // cols
    label_height = sheet_height // rows
    labels_per_sheet = cols * rows

    total_sheets = math.ceil(len(labels) / labels_per_sheet)
    sheets = []

    # Use specified font family
    try:
        if font_family == "ComicSansMS":
            if bold:
                font = ImageFont.truetype(
                    "/usr/share/fonts/truetype/msttcorefonts/Comic_Sans_MS_Bold.ttf",
                    font_size,
                )
            else:
                font = ImageFont.truetype(
                    "/usr/share/fonts/truetype/msttcorefonts/Comic_Sans_MS.ttf",
                    font_size,
                )
        else:
            if bold:
                font = ImageFont.truetype(
                    f"/usr/share/fonts/truetype/dejavu/{font_family}-Bold.ttf",
                    font_size,
                )
            else:
                font = ImageFont.truetype(
                    f"/usr/share/fonts/truetype/dejavu/{font_family}.ttf", font_size
                )
    except IOError:
        print(f"Failed to load {font_family}, using default font")
        font = ImageFont.load_default()
        font_size = 10  # Default font is typically around 10px

    print(f"Using font: {font} with size: {font_size}")

    for sheet_index in range(total_sheets):
        sheet = Image.new("RGB", (sheet_width, sheet_height), "white")
        draw = ImageDraw.Draw(sheet)

        for idx in range(labels_per_sheet):
            global_idx = sheet_index * labels_per_sheet + idx
            if global_idx >= len(labels):
                break
            label = labels[global_idx]
            # Calculate position
            x = (idx % cols) * label_width
            y = (idx // cols) * label_height
            lines = label.split("\n")
            total_text_height = len(lines) * (font_size + 4)
            start_y = y + (label_height - total_text_height) // 2
            for i, line in enumerate(lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                text_x = x + (label_width - text_width) // 2
                text_y = start_y + i * (font_size + 4)
                draw.text((text_x, text_y), line, fill="black", font=font)

        sheets.append(sheet)

    return sheets


@app.post("/generate")
async def generate_labels(
    label_data: str = Form(...),
    font_size: int = Form(24),
    bold: bool = Form(False),
    rows: int = Form(10),
    columns: int = Form(3),
    font_family: str = Form("DejaVuSans"),
    variables: str = Form("{}"),
):
    print(f"Received font size: {font_size} (type: {type(font_size)})")
    print(f"Received bold setting: {bold} (type: {type(bold)})")

    # Ensure font_size is a valid integer
    try:
        font_size = int(font_size)
        if font_size < 8 or font_size > 72:
            print(f"Font size {font_size} out of range, defaulting to 24")
            font_size = 24  # Default to 24 if out of range
    except (ValueError, TypeError) as e:
        print(f"Error converting font size: {e}")
        font_size = 24  # Default to 24 if conversion fails

    print(f"Using font size: {font_size}")

    # Parse variables
    try:
        variables_dict = json.loads(variables) if variables else {}
    except json.JSONDecodeError:
        variables_dict = {}

    labels = parse_input(label_data, variables_dict)
    sheets = create_label_sheets(
        labels,
        font_size=font_size,
        bold=bold,
        rows=rows,
        columns=columns,
        font_family=font_family,
    )

    img_io = io.BytesIO()
    sheets[0].save(
        img_io,
        format="PDF",
        save_all=True,
        append_images=sheets[1:],
        resolution=203.0,  # Set to 203 DPI for thermal printer
    )
    img_io.seek(0)
    return StreamingResponse(
        img_io,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=labels.pdf"},
    )


@app.post("/preview")
async def preview_labels(
    label_data: str = Form(...),
    font_size: int = Form(24),
    bold: bool = Form(True),
    rows: int = Form(10),
    columns: int = Form(3),
    font_family: str = Form("DejaVuSans"),
    variables: str = Form("{}"),
):
    print(f"Preview request received:")
    print(f"Label data: {label_data}")
    print(f"Font size: {font_size} (type: {type(font_size)})")
    print(f"Bold: {bold}")
    print(f"Rows: {rows}")
    print(f"Columns: {columns}")
    print(f"Font Family: {font_family}")
    print(f"Variables: {variables}")

    # Ensure font_size is a valid integer
    try:
        font_size = int(font_size)
        if font_size < 8 or font_size > 72:
            print(f"Font size {font_size} out of range, defaulting to 24")
            font_size = 24  # Default to 24 if out of range
    except (ValueError, TypeError) as e:
        print(f"Error converting font size: {e}")
        font_size = 24  # Default to 24 if conversion fails

    print(f"Using font size: {font_size}")

    # Parse variables
    try:
        variables_dict = json.loads(variables) if variables else {}
    except json.JSONDecodeError:
        variables_dict = {}

    labels = parse_input(label_data, variables_dict)
    print(f"Parsed labels: {labels}")

    sheets = create_label_sheets(
        labels,
        font_size=font_size,
        bold=bold,
        rows=rows,
        columns=columns,
        font_family=font_family,
    )
    print(f"Created {len(sheets)} sheets")

    # Save all preview images to static directory
    preview_urls = []
    for i, sheet in enumerate(sheets):
        preview_path = static_dir / f"preview_{i}.png"
        sheet.save(preview_path, format="PNG")
        preview_urls.append(f"/static/preview_{i}.png")
        print(f"Saved preview {i} to {preview_path}")

    # Return the paths to all saved images
    return {"preview_urls": preview_urls}


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8777, reload=True)
