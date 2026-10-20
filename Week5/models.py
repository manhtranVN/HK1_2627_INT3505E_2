from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Integer, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import mapped_column, relationship

db = SQLAlchemy()

class Category(db.Model):
    """Thể loại sách (Genre / Category) theo Slide 17 & 29"""
    __tablename__ = "categories"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    name = mapped_column(String(100), nullable=False)
    slug = mapped_column(String(100), unique=True, nullable=False)

    books = relationship("Book", back_populates="category", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug
        }


class Author(db.Model):
    """Tác giả theo Slide 16 & 17"""
    __tablename__ = "authors"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    name = mapped_column(String(100), nullable=False)
    bio = mapped_column(Text, nullable=True)

    book_authors = relationship("BookAuthor", back_populates="author", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "bio": self.bio
        }


class BookAuthor(db.Model):
    """Junction table quan hệ N:M giữa Book và Author kèm metadata role theo Slide 11"""
    __tablename__ = "book_authors"

    book_id = mapped_column(Integer, ForeignKey("books.id", ondelete="CASCADE"), primary_key=True)
    author_id = mapped_column(Integer, ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True)
    role = mapped_column(String(50), default="co", nullable=False)  # lead, co, ed

    book = relationship("Book", back_populates="book_authors")
    author = relationship("Author", back_populates="book_authors")

    def to_dict(self):
        return {
            "book_id": self.book_id,
            "author_id": self.author_id,
            "role": self.role,
            "author_name": self.author.name if self.author else None
        }


class Book(db.Model):
    """Thực thể Sách theo Slide 13, 16, 17"""
    __tablename__ = "books"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    title = mapped_column(String(200), nullable=False)
    isbn = mapped_column(String(13), unique=True, nullable=True)
    price_vnd = mapped_column(Integer, nullable=False, default=0)
    stock = mapped_column(Integer, default=0, nullable=False)
    category_id = mapped_column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    created_at = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    category = relationship("Category", back_populates="books")
    book_authors = relationship("BookAuthor", back_populates="book", cascade="all, delete-orphan", lazy="selectin")
    reviews = relationship("Review", back_populates="book", cascade="all, delete-orphan")

    @classmethod
    def from_payload(cls, payload):
        """Khởi tạo thực thể Book từ JSON payload theo Slide 15"""
        price_val = 0
        if isinstance(payload.get("price"), dict):
            price_val = payload["price"].get("amount", 0)
        elif isinstance(payload.get("price"), (int, float)):
            price_val = int(payload["price"])
        elif "price_vnd" in payload:
            price_val = int(payload["price_vnd"])

        book = cls(
            title=payload["title"],
            isbn=payload.get("isbn"),
            price_vnd=price_val,
            stock=payload.get("stock", 0),
            category_id=payload.get("category_id")
        )
        return book

    def to_dict(self, fields=None):
        """API Representation theo chuẩn Slide 13 & 27 (hỗ trợ sparse fieldsets)"""
        author_list = []
        for ba in self.book_authors:
            author_list.append({
                "id": ba.author_id,
                "name": ba.author.name if ba.author else None,
                "role": ba.role
            })

        full = {
            "id": f"book_{self.id}",
            "raw_id": self.id,
            "title": self.title,
            "isbn": self.isbn,
            "category": self.category.to_dict() if self.category else None,
            "genre": self.category.slug if self.category else None,
            "authors": author_list,
            "price": {
                "amount": self.price_vnd,
                "currency": "VND"
            },
            "stock": self.stock,
            "inStock": self.stock > 0,
            "createdAt": self.created_at.strftime("%Y-%m-%dT%H:%M:%SZ") if self.created_at else None
        }

        if fields is None:
            return full

        # Xử lý trường hợp chỉ chọn các trường theo query param ?fields=...
        requested_fields = set(f.strip() for f in fields.split(",") if f.strip())
        return {k: v for k, v in full.items() if k in requested_fields or (k == "raw_id" and "id" in requested_fields)}


class User(db.Model):
    """Người dùng hệ thống theo Slide 17"""
    __tablename__ = "users"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    email = mapped_column(String(255), unique=True, nullable=False)
    display_name = mapped_column(String(120), nullable=False)

    reviews = relationship("Review", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "display_name": self.display_name
        }


class Review(db.Model):
    """Đánh giá sách theo Slide 9, 12, 17"""
    __tablename__ = "reviews"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    rating = mapped_column(Integer, nullable=False)  # 1-5
    comment = mapped_column(Text, nullable=True)
    book_id = mapped_column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    user_id = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    book = relationship("Book", back_populates="reviews")
    user = relationship("User", back_populates="reviews")

    def to_dict(self):
        return {
            "id": self.id,
            "rating": self.rating,
            "comment": self.comment,
            "book_id": self.book_id,
            "user_id": self.user_id,
            "author_name": self.user.display_name if self.user else None,
            "created_at": self.created_at.strftime("%Y-%m-%dT%H:%M:%SZ") if self.created_at else None
        }
