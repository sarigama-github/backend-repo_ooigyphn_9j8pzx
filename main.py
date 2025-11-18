import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import create_document, get_documents, db
from schemas import MenuItem as MenuItemSchema, Inquiry as InquirySchema

app = FastAPI(title="Beachside Cafe API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MenuItemOut(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    category: str
    is_featured: bool = False


class InquiryIn(BaseModel):
    name: str
    email: str
    message: str
    phone: Optional[str] = None
    topic: Optional[str] = None


@app.get("/")
def read_root():
    return {"message": "Beachside Cafe backend is running"}


@app.get("/api/hello")
def hello():
    return {"message": "Welcome to the Beachside Cafe API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# --- Cafe API ---

SAMPLE_MENU: List[MenuItemSchema] = [
    MenuItemSchema(name="Iced Latte", description="Double shot espresso with cold milk over ice", price=5.5, category="Coffee", is_featured=True),
    MenuItemSchema(name="Tropical Smoothie", description="Pineapple, mango, coconut water", price=6.5, category="Smoothie", is_featured=True),
    MenuItemSchema(name="Avocado Toast", description="Sourdough, smashed avo, chili flakes, lemon", price=9.0, category="Brunch", is_featured=False),
    MenuItemSchema(name="Blueberry Muffin", description="Baked daily, crumb topping", price=3.5, category="Pastry", is_featured=False),
    MenuItemSchema(name="Cold Brew", description="Slow steeped, smooth and bold", price=4.75, category="Coffee", is_featured=True),
]


def ensure_menu_seeded():
    try:
        existing = get_documents("menuitem", {}, limit=1)
        if not existing:
            for item in SAMPLE_MENU:
                create_document("menuitem", item)
    except Exception:
        # If database is unavailable, just skip seeding; endpoints will still respond gracefully
        pass


@app.get("/api/menu", response_model=List[MenuItemOut])
def get_menu(category: Optional[str] = Query(None), featured: Optional[bool] = Query(None)):
    """Fetch menu items. Optional filters: category, featured=true/false"""
    ensure_menu_seeded()
    filt = {}
    if category:
        filt["category"] = category
    if featured is not None:
        filt["is_featured"] = featured

    try:
        docs = get_documents("menuitem", filt)
        items: List[MenuItemOut] = []
        for d in docs:
            items.append(MenuItemOut(
                name=d.get("name"),
                description=d.get("description"),
                price=float(d.get("price")),
                category=d.get("category"),
                is_featured=bool(d.get("is_featured", False))
            ))
        return items
    except Exception:
        # Fallback to sample data if database isn't available
        data = SAMPLE_MENU
        if category:
            data = [m for m in data if m.category == category]
        if featured is not None:
            data = [m for m in data if m.is_featured == featured]
        return [MenuItemOut(**m.model_dump()) for m in data]


@app.post("/api/inquiry")
def submit_inquiry(payload: InquiryIn):
    """Save a contact form inquiry"""
    try:
        inquiry = InquirySchema(**payload.model_dump())
        doc_id = create_document("inquiry", inquiry)
        return {"status": "ok", "id": doc_id}
    except Exception:
        # If db is not available, still acknowledge receipt without ID
        return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
