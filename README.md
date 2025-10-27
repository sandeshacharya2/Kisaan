किसान (Kisaan) – Smart Agriculture Platform

किसान is a Django-based web application designed to connect farmers and customers in one digital marketplace. The system simplifies agricultural trade by allowing farmers to sell their products online and customers to purchase fresh goods directly from verified farmers.

🚀 Features
👨‍🌾 Farmer Module

Farmer registration with email verification (OTP)

Add profile details (address, ward, phone number, photo)

Post agricultural products with images, descriptions, and prices

Accept or reject bids from customers

Track sales, total income, and active listings

View dashboard with all product and bid summaries

🧑‍💼 Customer Module

Customer registration with OTP verification

Browse and search for agricultural products

Filter products by location, price, and category

Place bids or buy directly from farmers

Chat or message farmers for inquiries

🌍 Location & Map Integration

Farmers can set selling location via

Beni Municipality Ward Dropdown (1–10), and

Google Maps / HTML5 Geolocation support

🔐 Authentication & Security

Separate login systems for Farmers and Customers

Password encryption using Django’s built-in auth system

Email verification before registration completion

📊 Dashboard & Interface

Role-based dashboard after login

Navigation links for:

Home

About

Contact

Dashboard (Farmer or Customer)

Logout

🛠️ Tech Stack
Layer	Technology
Backend	Django (Python)
Frontend	HTML5, CSS3, TailwindCSS
Database	SQLite3 (Default Django DB)
Map Integration	Google Maps / HTML5 Geolocation
Authentication	Django built-in auth with OTP email verification
Language Support	English + Nepali (i18n
