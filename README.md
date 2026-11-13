# 🍔 BulkBite

> **Founder: KEDAR PATIL**  
> **Zero Delivery Fee Group Ordering Platform for Hostel Students**  
> Stop paying ₹40 delivery charges on a ₹30 craving. Pool together, hit the ₹200 free delivery threshold, and meet at the gate!

---

## 🌟 The Problem BulkBite Solves
In hostels and university campuses, students often crave late-night snacks, energy drinks, instant noodles, stationery, or groceries worth ₹20–₹40 on quick-commerce apps like **Blinkit**, **Zepto**, **Swiggy Instamart**, and **Zomato**.

However, quick commerce platforms charge **₹30–₹40 delivery fees** unless the cart exceeds the minimum free delivery threshold (typically **₹199–₹200**). Paying ₹40 delivery on a ₹20 drink doubles the cost.

**BulkBite** connects hostelers living in the same building:
1. One student **hosts an order** (e.g. Blinkit, ordering at 11:30 PM, target ₹200).
2. Other students receive instant **live notifications with room numbers**, add what they want (with product links, quantities, and prices).
3. The real-time **Free Delivery Progress Bar** tracks the cart as it climbs towards ₹200.
4. When the target is reached, the host locks the pool and places the bulk order.
5. The host updates the delivery ETA, and when the delivery boy arrives, triggers the **🚨 Gate Alert**.
6. All purchasers meet at the gate at the exact time to collect their items and settle their share via **UPI QR Code** or 1-tap mobile payment.

---

## 🔒 One Student, One Account (Authentication & Privacy)

The platform enforces **individual accounts with password protection**:
- **Personal Sign Up**: Each student creates their own account with:
  - **Full Name**
  - **Room Number** (e.g., Room 304)
  - **Hostel / Wing / Block** (e.g., Hostel 3 Boys, Hostel 1 Girls)
  - **Phone / WhatsApp Number** (unique login identifier)
  - **Secure Password** (hashed with SHA-256 + salt)
  - **UPI ID** (for receiving cashless payments when hosting)
- **Role Permissions & Security**:
  - No public switcher: Students only have access to their own account.
  - **Only the host** of a pool can change the order status (e.g., Lock cart, enter ETA, trigger Gate Arrival broadcast). Other students attempting to alter another host's pool receive `403 Forbidden`.
  - **Only the item owner or pool host** can remove an item from the cart.
  - Sessions use bearer tokens stored securely and validated on every API call.
- **Demo Student Logins** (Pre-seeded for testing):
  - **Rahul Sharma (Room 304)**: Phone `9876543210` | Password `hostel123`
  - **Aman Verma (Room 210)**: Phone `9811223344` | Password `hostel123`
  - **Priya Nair (Room 102)**: Phone `9822334455` | Password `hostel123`

---

## 🛠️ Tech Stack & Architecture

- **Creator & Founder**: Kedar Patil
- **Backend**: Python 3 standard library (`http.server.ThreadingHTTPServer`, `sqlite3`, `hashlib`, `secrets`, `json`).
  - **Zero external pip dependencies required** — runs out of the box on any machine with Python 3!
  - Fully multi-threaded REST API server.
- **Database**: SQLite3 (`hostel_pool.db`) with `users`, `sessions`, `pools`, `pool_items`, `payments`, and `notifications`.
- **Frontend**: Pure Vanilla HTML5, CSS3, and modern ES6 JavaScript.
  - Mobile-first, responsive hostel dashboard.
  - Dark / Light mode toggle.
  - Web Audio API for alert chimes.
  - Offline SVG QR code engine for UPI payments.

---

## 🏃 How to Run BulkBite

1. Open PowerShell or Terminal and navigate to the project folder:
   ```powershell
   cd C:\Users\Asus\.gemini\antigravity\scratch\hostel-cart-pool
   ```

2. Start the local server:
   ```powershell
   python server.py
   ```
   *(Or double-click `run.bat`)*

3. Open your browser and go to:
   ```
   http://localhost:8080
   ```
