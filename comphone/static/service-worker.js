// comphone/static/service-worker.js

self.addEventListener('push', function(event) {
    // ตรวจสอบว่ามีข้อมูลส่งมากับการแจ้งเตือนหรือไม่
    if (!event.data) {
        console.error('Push event but no data');
        return;
    }

    const data = event.data.json();
    console.log('Push notification received:', data);

    const title = data.title || "Comphone Service";
    const options = {
        body: data.body,
        icon: data.icon || '/static/logo.png', // ไอคอนหลัก
        badge: '/static/logo.png', // ไอคอนเล็กๆ บนแถบแจ้งเตือน (Android)
        vibrate: [100, 50, 100], // สั่น [สั่น, หยุด, สั่น]
        data: {
            url: data.url || '/' // URL ที่จะเปิดเมื่อคลิกการแจ้งเตือน
        }
    };

    // แสดงการแจ้งเตือน
    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

// จัดการเมื่อผู้ใช้คลิกที่การแจ้งเตือน
self.addEventListener('notificationclick', function(event) {
    // ปิดการแจ้งเตือนที่คลิก
    event.notification.close();

    // เปิดหน้าต่างใหม่ไปยัง URL ที่ระบุ หรือไปยังหน้าหลัก
    event.waitUntil(
        clients.openWindow(event.notification.data.url)
    );
});
