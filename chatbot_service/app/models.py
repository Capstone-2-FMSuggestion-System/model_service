from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    address = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    role = Column(String(20), default="customer")

    # Relationships
    cart_items = relationship("CartItems", back_populates="user")
    orders = relationship("Orders", back_populates="user")
    reviews = relationship("Reviews", back_populates="user")
    favorite_menus = relationship("FavoriteMenus", back_populates="user")
    chat_sessions = relationship("ChatSessions", back_populates="user")
    chat_messages = relationship("ChatMessages", back_populates="user")


class Category(Base):
    __tablename__ = "categories"

    category_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String(255), nullable=True)

    # Relationships
    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"

    product_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    image_url = Column(String(255), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.category_id"))
    nutrition_info = Column(Text, nullable=True)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    category = relationship("Category", back_populates="products")
    cart_items = relationship("CartItems", back_populates="product")
    order_items = relationship("OrderItems", back_populates="product")
    inventory = relationship("Inventory", back_populates="product")
    menu_items = relationship("MenuItems", back_populates="product")
    reviews = relationship("Reviews", back_populates="product")


class CartItems(Base):
    __tablename__ = "cart_items"

    cart_item_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    product_id = Column(Integer, ForeignKey("products.product_id"))
    quantity = Column(Integer, default=1)
    added_at = Column(DateTime, default=func.now())

    # Relationships
    user = relationship("User", back_populates="cart_items")
    product = relationship("Product", back_populates="cart_items")


class Orders(Base):
    __tablename__ = "orders"

    order_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    total_amount = Column(Float, nullable=False)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    shipping_address = Column(String(255), nullable=True)
    payment_method = Column(String(50), nullable=True)

    # Relationships
    user = relationship("User", back_populates="orders")
    order_items = relationship("OrderItems", back_populates="order")
    payments = relationship("Payments", back_populates="order")


class OrderItems(Base):
    __tablename__ = "order_items"

    order_item_id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.order_id"))
    product_id = Column(Integer, ForeignKey("products.product_id"))
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)

    # Relationships
    order = relationship("Orders", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")


class Inventory(Base):
    __tablename__ = "inventory"

    inventory_id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.product_id"))
    quantity = Column(Integer, default=0)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    product = relationship("Product", back_populates="inventory")
    transactions = relationship("InventoryTransactions", back_populates="inventory")


class InventoryTransactions(Base):
    __tablename__ = "inventory_transactions"

    transaction_id = Column(Integer, primary_key=True, autoincrement=True)
    inventory_id = Column(Integer, ForeignKey("inventory.inventory_id"))
    quantity_change = Column(Integer, nullable=False)
    transaction_type = Column(String(20), nullable=False)  # 'in' or 'out'
    reason = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    inventory = relationship("Inventory", back_populates="transactions")


class Menus(Base):
    __tablename__ = "menus"

    menu_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    is_public = Column(Boolean, default=False)

    # Relationships
    menu_items = relationship("MenuItems", back_populates="menu")
    favorite_menus = relationship("FavoriteMenus", back_populates="menu")


class MenuItems(Base):
    __tablename__ = "menu_items"

    menu_item_id = Column(Integer, primary_key=True, autoincrement=True)
    menu_id = Column(Integer, ForeignKey("menus.menu_id"))
    product_id = Column(Integer, ForeignKey("products.product_id"))
    quantity = Column(Integer, default=1)

    # Relationships
    menu = relationship("Menus", back_populates="menu_items")
    product = relationship("Product", back_populates="menu_items")


class FavoriteMenus(Base):
    __tablename__ = "favorite_menus"

    favorite_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    menu_id = Column(Integer, ForeignKey("menus.menu_id"))
    created_at = Column(DateTime, default=func.now())

    # Relationships
    user = relationship("User", back_populates="favorite_menus")
    menu = relationship("Menus", back_populates="favorite_menus")


class Reviews(Base):
    __tablename__ = "reviews"

    review_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    product_id = Column(Integer, ForeignKey("products.product_id"))
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="reviews")
    product = relationship("Product", back_populates="reviews")


class Promotions(Base):
    __tablename__ = "promotions"

    promotion_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    discount_percent = Column(Float, nullable=True)
    discount_amount = Column(Float, nullable=True)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())


class Payments(Base):
    __tablename__ = "payments"

    payment_id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.order_id"))
    amount = Column(Float, nullable=False)
    payment_method = Column(String(50), nullable=False)
    status = Column(String(20), default="pending")
    transaction_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    order = relationship("Orders", back_populates="payments")


class ChatSessions(Base):
    __tablename__ = "chat_sessions"

    session_id = Column(String(255), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    question_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessages", back_populates="session")


class ChatMessages(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), ForeignKey("chat_sessions.session_id"))
    user_id = Column(Integer, ForeignKey("users.user_id"))
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=func.now())

    # Relationships
    session = relationship("ChatSessions", back_populates="messages")
    user = relationship("User", back_populates="chat_messages")