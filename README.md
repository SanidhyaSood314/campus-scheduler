# 🏛️ Campus Scheduler

A smart and efficient **venue booking system** designed for campuses to manage events, avoid scheduling conflicts, and streamline approvals through an admin-controlled workflow.

---

## 🚀 Features

* 📅 **Venue Booking System**
  Users can request bookings for different venues across campus.

* ⚠️ **Conflict Detection**
  Automatically prevents overlapping bookings for the same venue and time.

* 🛠️ **Admin Approval Workflow**

  * Approve or reject booking requests
  * Ensures controlled and verified scheduling

* 📊 **Dashboard & Analytics**
  Visual insights into bookings, status distribution, and usage trends.

* 🔐 **Admin Authentication**
  Secure access to admin functionalities using session-based authentication.

* ✏️ **Edit & Manage Bookings**
  Users can modify pending bookings; admins can manage all bookings.

---

## 🧠 Problem Statement

Managing venue bookings manually often leads to:

* Double bookings
* Lack of transparency
* Inefficient approval processes

This project solves these issues by providing a **centralized and automated booking platform**.

---

## 🏗️ Tech Stack

* **Frontend:** HTML, CSS, JavaScript
* **Backend:** Python (Flask) 
* **Database:** SQLite
* **Visualization:** Chart.js

---

## ⚙️ How It Works

1. User submits a booking request
2. System checks for time conflicts
3. Booking is marked as **Pending**
4. Admin reviews and:

   * ✅ Approves → Booking confirmed
   * ❌ Rejects → Booking denied

---

## 📁 Project Structure

```
campus-scheduler/
│
├── app.py           # Flask backend
├── index.html       # Frontend UI
├── venues.json      # Venue data
├── requirements.txt # Dependencies
└── README.md
```

---

## 🧪 Local Setup

### 1. Clone / Download the project

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the server

```bash
python app.py
```

### 4. Open in browser

```
http://127.0.0.1:5000
```

---

## 🌐 Deployment

* **Backend:** Render
* **Frontend:** Vercel

---


## 🌐 Live Demo

* **Frontend (UI):** https://your-frontend-url.vercel.app
* **Backend API:** https://your-backend-url.onrender.com

---

## 📡 API Endpoints (Quick Access)

* Get all bookings:
  `GET /bookings`

* Create booking:
  `POST /book`

* Admin login:
  `POST /admin/login`

* Approve booking:
  `PUT /approve/<id>`

---

## 🧪 Quick Test

1. Open the frontend link
2. Create a booking
3. Go to “Pending” tab
4. Login as admin
5. Approve the booking

---


## 🔑 Admin Access

Default password:

```
admin123
```

👉 Can be changed using environment variables:

```
ADMIN_PASSWORD=your_password
```

---

## ⚠️ Limitations

* Uses SQLite (data resets on redeploy in Render)
* Not optimized for large-scale production yet

---

## 🚀 Future Improvements

* 🔐 JWT Authentication
* ☁️ Cloud database (PostgreSQL)
* 📱 Mobile responsiveness enhancements
* 🔔 Notification system
* 📆 Calendar integration

---

## 🤝 Contributing

Feel free to fork the project and submit improvements!

---

## 📜 License

This project is licensed under the MIT License.

---

## 💡 Inspiration

Built to simplify and modernize campus event management systems with a clean UI and robust backend logic.

---

## 👨‍💻 Author

Developed for hackathon purposes with focus on **practical usability and real-world impact**.

---
