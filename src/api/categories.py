"""Category API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.category import Category as CategoryModel
from src.schemas.category import Category, CategoryCreate

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])


@router.post("/", response_model=Category, status_code=201)
def create_category(category: CategoryCreate, db: Session = Depends(get_db)) -> CategoryModel:
    """Create a new category."""
    # Check if category with same name exists
    existing = db.query(CategoryModel).filter(CategoryModel.name == category.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category with this name already exists")

    db_category = CategoryModel(**category.model_dump())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


@router.get("/", response_model=list[Category])
def list_categories(db: Session = Depends(get_db)) -> list[CategoryModel]:
    """List all categories."""
    return db.query(CategoryModel).all()


@router.get("/{category_id}", response_model=Category)
def get_category(category_id: int, db: Session = Depends(get_db)) -> CategoryModel:
    """Get a category by ID."""
    category = db.query(CategoryModel).filter(CategoryModel.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.delete("/{category_id}", status_code=204)
def delete_category(category_id: int, db: Session = Depends(get_db)) -> None:
    """Delete a category."""
    category = db.query(CategoryModel).filter(CategoryModel.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    db.delete(category)
    db.commit()
