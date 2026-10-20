from datetime import datetime, timezone, timedelta
from models import db, Category, Author, Book, BookAuthor, User, Review

def seed_database():
    if db.session.scalar(db.select(db.func.count(Category.id))) > 0:
        return

    cats = [
        Category(name="Công nghệ thông tin", slug="tech"),
        Category(name="Khoa học", slug="science"),
        Category(name="Văn học & Tiểu thuyết", slug="fiction"),
        Category(name="Kinh tế & Khởi nghiệp", slug="business"),
        Category(name="Tâm lý & Kỹ năng", slug="psychology"),
    ]
    db.session.add_all(cats)
    db.session.flush()

    cat_map = {c.slug: c.id for c in cats}

    authors = [
        Author(name="Robert C. Martin", bio="Tác giả nổi tiếng về Clean Code và Clean Architecture."),
        Author(name="Martin Fowler", bio="Chuyên gia về kiến trúc phần mềm và Refactoring."),
        Author(name="Andrew Hunt", bio="Đồng tác giả cuốn The Pragmatic Programmer."),
        Author(name="David Thomas", bio="Đồng tác giả cuốn The Pragmatic Programmer."),
        Author(name="Eric Evans", bio="Tác giả của Domain-Driven Design (DDD)."),
        Author(name="Carl Sagan", bio="Nhà thiên văn học, tác giả cuốn Cosmos."),
        Author(name="Stephen Hawking", bio="Nhà vật lý lý thuyết, tác giả A Brief History of Time."),
        Author(name="George Orwell", bio="Tác giả các tác phẩm kinh điển 1984 và Animal Farm."),
        Author(name="Yuval Noah Harari", bio="Sử gia, tác giả cuốn Sapiens: Lược sử loài người."),
        Author(name="Peter Thiel", bio="Doanh nhân, tác giả cuốn Zero to One."),
    ]
    db.session.add_all(authors)
    db.session.flush()

    author_map = {a.name: a.id for a in authors}

    users = [
        User(email="an.nguyen@example.com", display_name="Nguyễn Văn An"),
        User(email="binh.tran@example.com", display_name="Trần Thị Bình"),
        User(email="cuong.le@example.com", display_name="Lê Văn Cường"),
    ]
    db.session.add_all(users)
    db.session.flush()

    now = datetime.now(timezone.utc)
    raw_books = [
        ("Clean Code", "9780132350884", 350000, 15, cat_map["tech"], [("Robert C. Martin", "lead")]),
        ("Clean Architecture", "9780134494166", 420000, 20, cat_map["tech"], [("Robert C. Martin", "lead")]),
        ("The Pragmatic Programmer", "9780201616224", 350000, 12, cat_map["tech"], [("Andrew Hunt", "lead"), ("David Thomas", "co")]),
        ("Refactoring", "9780201485677", 450000, 8, cat_map["tech"], [("Martin Fowler", "lead")]),
        ("Domain-Driven Design", "9780321125217", 480000, 5, cat_map["tech"], [("Eric Evans", "lead")]),
        ("Patterns of Enterprise Application Architecture", "9780321127426", 520000, 7, cat_map["tech"], [("Martin Fowler", "lead")]),
        ("Clean Craftsmanship", "9780136921837", 350000, 0, cat_map["tech"], [("Robert C. Martin", "lead")]),
        ("Extreme Programming Explained", "9780201616415", 300000, 10, cat_map["tech"], [("Martin Fowler", "co")]),
        ("The Clean Coder", "9780137081073", 350000, 18, cat_map["tech"], [("Robert C. Martin", "lead")]),

        ("Cosmos", "9780345331359", 250000, 25, cat_map["science"], [("Carl Sagan", "lead")]),
        ("Pale Blue Dot", "9780345376596", 260000, 14, cat_map["science"], [("Carl Sagan", "lead")]),
        ("A Brief History of Time", "9780553380163", 220000, 30, cat_map["science"], [("Stephen Hawking", "lead")]),
        ("The Grand Design", "9780553384666", 250000, 11, cat_map["science"], [("Stephen Hawking", "lead")]),
        ("The Demon-Haunted World", "9780345409461", 270000, 9, cat_map["science"], [("Carl Sagan", "lead")]),

        ("1984", "9780451524935", 150000, 50, cat_map["fiction"], [("George Orwell", "lead")]),
        ("Animal Farm", "9780451526342", 120000, 45, cat_map["fiction"], [("George Orwell", "lead")]),
        ("Homage to Catalonia", "9780156421171", 180000, 10, cat_map["fiction"], [("George Orwell", "lead")]),
        ("Burmese Days", "9780156148504", 170000, 6, cat_map["fiction"], [("George Orwell", "lead")]),

        ("Zero to One", "9780804139297", 200000, 35, cat_map["business"], [("Peter Thiel", "lead")]),
        ("Sapiens: A Brief History of Humankind", "9780062316097", 320000, 40, cat_map["business"], [("Yuval Noah Harari", "lead")]),
        ("Homo Deus: A Brief History of Tomorrow", "9780062464316", 330000, 22, cat_map["business"], [("Yuval Noah Harari", "lead")]),
        ("21 Lessons for the 21st Century", "9780525512172", 310000, 19, cat_map["business"], [("Yuval Noah Harari", "lead")]),

        ("Thinking, Fast and Slow", "9780374533557", 290000, 28, cat_map["psychology"], []),
        ("Atomic Habits", "9780735211292", 210000, 60, cat_map["psychology"], []),
        ("Deep Work", "9781455586691", 230000, 16, cat_map["psychology"], []),
    ]

    for idx, (title, isbn, price, stock, cat_id, author_links) in enumerate(raw_books):
        book = Book(
            title=title,
            isbn=isbn,
            price_vnd=price,
            stock=stock,
            category_id=cat_id,
            created_at=now - timedelta(days=idx)
        )
        db.session.add(book)
        db.session.flush()

        for author_name, role in author_links:
            aid = author_map.get(author_name)
            if aid:
                ba = BookAuthor(book_id=book.id, author_id=aid, role=role)
                db.session.add(ba)

    clean_code_book = db.session.scalar(db.select(Book).where(Book.title == "Clean Code"))
    if clean_code_book and users:
        db.session.add_all([
            Review(rating=5, comment="Sách gối đầu giường cho lập trình viên!", book_id=clean_code_book.id, user_id=users[0].id),
            Review(rating=4, comment="Nội dung rất hay và thực tế.", book_id=clean_code_book.id, user_id=users[1].id),
        ])

    db.session.commit()
    print("Seeded database successfully!")
