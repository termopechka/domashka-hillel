import json

class ShopManager:
    _instance = None

    def __new__(cls, filepath='store.json'):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.filepath = filepath
            with open(filepath, 'r', encoding='utf-8') as f:
                cls._instance.data = json.load(f)
        return cls._instance

    def save(self):
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)


class Product:
    def __init__(self, name, category, price, quantity):
        self.name = name
        self.category = category
        self.price = price
        self.quantity = quantity
        self.manager = ShopManager()
        self.details = self.manager.data['products'].get(name)

    def set_price(self, new_price):
        if self.details:
            self.details['price'] = new_price
            self.manager.save()

    def set_stock(self, quantity):
        if self.details:
            self.details['stock'] = quantity
            self.manager.save()


class Customer:
    def __init__(self, name, email):
        self.name = name
        self.email = email
        self.orders = []

    def add_order(self, order):
        self.orders.append(order)


class Order:
    def __init__(self):
        self.items = []
        self.total_sum = 0

    def add_product(self, product_name, price):
        self.items.append({"name": product_name, "price": price})
        self.calculate_total()

    def calculate_total(self):
        self.total_sum = sum(item['price'] for item in self.items)
        return self.total_sum


shop = ShopManager()

apple = Product('apple', 'food', 100, 20)
banana = Product('banana', 'food', 150, 10)
apple.set_price(200)
banana.set_price(100)

ivan = Customer("Ivan", "ivan@mail.com")
new_order = Order()
new_order.add_product("apple", shop.data['products']['apple']['price'])
ivan.add_order(new_order)
print(new_order)
