from fastapi import APIRouter, HTTPException
from app.services.database.database import db
from typing import Dict, Any, List, Optional
from decimal import Decimal
import logging
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import uuid4

router = APIRouter()
logger = logging.getLogger(__name__)

# Define response models


class Product(BaseModel):
    id: int
    image_url: Optional[str]
    name: str
    status: str
    price: Decimal
    stock: int
    available_at: datetime


class ProductResponse(BaseModel):
    status: str
    count: int
    products: List[Product]


class SingleProductResponse(BaseModel):
    status: str
    product: Product


class ProductStats(BaseModel):
    status: str
    total_products: int
    total_stock: int
    min_price: Decimal
    max_price: Decimal
    avg_price: float


class TotalStats(BaseModel):
    total_products: int
    in_stock_products: int
    total_stock: int


class StatsResponse(BaseModel):
    status: str
    status_stats: List[ProductStats]
    total_stats: TotalStats


class ProductCreate(BaseModel):
    name: str
    image_url: Optional[str] = None
    status: str = Field(...,
                        description="Product status (e.g., 'active', 'inactive')")
    price: Decimal = Field(..., ge=0)
    stock: int = Field(..., ge=0)
    available_at: Optional[datetime] = None


@router.get("/products", response_model=ProductResponse)
async def get_products(
    limit: int = 10,
    offset: int = 0,
    status: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    in_stock: Optional[bool] = None
):
    """Get products with optional filtering"""
    try:
        query = """
            SELECT id, image_url, name, status, price, stock, available_at
            FROM products
            WHERE 1=1
        """
        params = []

        if status:
            query += " AND status = $" + str(len(params) + 1)
            params.append(status)

        if min_price is not None:
            query += " AND price >= $" + str(len(params) + 1)
            params.append(Decimal(str(min_price)))

        if max_price is not None:
            query += " AND price <= $" + str(len(params) + 1)
            params.append(Decimal(str(max_price)))

        if in_stock is not None:
            query += " AND stock " + ("> 0" if in_stock else "= 0")

        # Add ordering and pagination
        query += """
            ORDER BY available_at DESC
            LIMIT $""" + str(len(params) + 1) + " OFFSET $" + str(len(params) + 2)

        params.extend([limit, offset])

        products = await db.fetch(query, *params)

        return {
            "status": "success",
            "count": len(products),
            "products": products
        }
    except Exception as e:
        logger.error(f"Error fetching products: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/products/{product_id}", response_model=SingleProductResponse)
async def get_product(product_id: int):
    """Get a specific product by ID"""
    try:
        product = await db.fetchrow("""
            SELECT id, image_url, name, status, price, stock, available_at
            FROM products
            WHERE id = $1
        """, product_id)

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        return {
            "status": "success",
            "product": product
        }
    except Exception as e:
        logger.error(f"Error fetching product {product_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/products/status/{status}", response_model=ProductResponse)
async def get_products_by_status(
    status: str,
    limit: int = 10,
    offset: int = 0
):
    """Get products by status"""
    try:
        products = await db.fetch("""
            SELECT id, image_url, name, status, price, stock, available_at
            FROM products
            WHERE status = $1
            ORDER BY available_at DESC
            LIMIT $2 OFFSET $3
        """, status, limit, offset)

        return {
            "status": "success",
            "product_status": status,
            "count": len(products),
            "products": products
        }
    except Exception as e:
        logger.error(f"Error fetching products for status {status}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/products/stats/summary", response_model=StatsResponse)
async def get_product_stats():
    """Get product statistics"""
    try:
        stats = await db.fetch("""
            SELECT 
                status,
                COUNT(*) as total_products,
                SUM(stock) as total_stock,
                MIN(price) as min_price,
                MAX(price) as max_price,
                AVG(price) as avg_price
            FROM products
            GROUP BY status
            ORDER BY total_products DESC
        """)

        # Get total counts
        total_counts = await db.fetchrow("""
            SELECT 
                COUNT(*) as total_products,
                SUM(CASE WHEN stock > 0 THEN 1 ELSE 0 END) as in_stock_products,
                SUM(stock) as total_stock
            FROM products
        """)

        return {
            "status": "success",
            "status_stats": stats,
            "total_stats": total_counts
        }
    except Exception as e:
        logger.error(f"Error fetching product stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/products/latest", response_model=ProductResponse)
async def get_latest_products(
    limit: int = 5,
    in_stock: Optional[bool] = None
):
    """Get the most recently available products"""
    try:
        query = """
            SELECT id, image_url, name, status, price, stock, available_at
            FROM products
            WHERE 1=1
        """
        params = [limit]

        if in_stock is not None:
            query += " AND stock " + ("> 0" if in_stock else "= 0")

        query += """
            ORDER BY available_at DESC
            LIMIT $1
        """

        products = await db.fetch(query, *params)

        return {
            "status": "success",
            "count": len(products),
            "products": products
        }
    except Exception as e:
        logger.error(f"Error fetching latest products: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/products", response_model=SingleProductResponse)
async def create_product(product: ProductCreate):
    """Create a new product"""
    try:
        if not product.available_at:
            product.available_at = datetime.utcnow()

        product_data = product.model_dump()

        # Get the last ID from the products table
        last_id = await db.fetchval("""
            SELECT COALESCE(MAX(id), 0) FROM products
        """)

        next_id = last_id + 1

        # Insert with explicit ID
        query = """
            INSERT INTO products (id, name, image_url, status, price, stock, available_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id, name, image_url, status, price, stock, available_at
        """

        new_product = await db.fetchrow(
            query,
            next_id,
            product_data['name'],
            product_data['image_url'],
            product_data['status'],
            product_data['price'],
            product_data['stock'],
            product_data['available_at']
        )

        return {
            "status": "success",
            "product": new_product
        }
    except Exception as e:
        logger.error(f"Error creating product: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
