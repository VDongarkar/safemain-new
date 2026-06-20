let map;
let marker;

document.addEventListener('DOMContentLoaded', () => {
    const uploadForm = document.getElementById('uploadForm');

    // 1. Initialize Map
    map = L.map('map').setView([18.6298, 73.7997], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

    window.updateMarker = (lat, lng) => {
        if (marker) map.removeLayer(marker);
        marker = L.marker([lat, lng]).addTo(map);
        document.getElementById('lat').value = lat;
        document.getElementById('lng').value = lng;
    };

    map.on('click', (e) => { updateMarker(e.latlng.lat, e.latlng.lng); });

    // 2. Detect Location with Area Detection
    window.detectLocation = async () => {
        if (!navigator.geolocation) return alert("Geolocation not supported.");
        
        navigator.geolocation.getCurrentPosition(async (position) => {
            const { latitude, longitude } = position.coords;
            map.setView([latitude, longitude], 16);
            updateMarker(latitude, longitude);
            
            // Get Area Name for the Alert
            try {
                const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}`);
                const data = await response.json();
                const area = data.address.suburb || data.address.road || "PCMC Area";
                alert("✅ Location Detected: " + area);
            } catch (e) {
                alert("✅ Location detected!");
            }
        }, () => alert("❌ Please enable GPS."));
    };

    // 3. Simple & Strong Submission Connected to Local Backend
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const submitBtn = uploadForm.querySelector('button[type="submit"]');
        const fileInput = document.getElementById('potholeImage');
        const lat = document.getElementById('lat').value;
        const lng = document.getElementById('lng').value;

        if (!lat || !lng) return alert("Please select a location on the map!");
        if (!fileInput.files[0]) return alert("Please upload a photo!");

        submitBtn.disabled = true;
        submitBtn.innerText = "⏳ AI Analyzing...";

        // Retrieve current logged-in user credentials from session memory
        const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
        const citizenName = currentUser.name || localStorage.getItem('safepath_user_name') || "Anonymous Citizen";
        const citizenPhone = currentUser.email || localStorage.getItem('safepath_user_phone') || "Unknown Phone"; // Matches email/identifier used at login

        const formData = new FormData();
        formData.append('image', fileInput.files[0]);
        formData.append('latitude', lat);
        formData.append('longitude', lng);
        formData.append('name', citizenName);
        formData.append('phone', citizenPhone);

        try {
            // Updated to securely point to the running local system loop backend
            const response = await fetch('http://127.0.0.1:5000/predict', { method: 'POST', body: formData });
            const data = await response.json();
            
            if (data.status === 'success') {
                const reports = JSON.parse(localStorage.getItem('safepath_reports') || '[]');
                
                const newReport = {
                    id: Date.now(),
                    lat: parseFloat(lat),
                    lng: parseFloat(lng),
                    severity: data.severity,
                    area: data.area,
                    reporter: citizenName,
                    status: 'Pending',
                    created: data.timestamp || new Date().toLocaleString()
                };

                reports.push(newReport);
                localStorage.setItem('safepath_reports', JSON.stringify(reports));

                // Success Alert
                alert(`✅ SUCCESS!\nArea: ${data.area}\nAI Severity: ${data.severity}`);

                // Update UI
                displayUserStatus();
                updateImpactCounter();
                
                uploadForm.reset();
                if (marker) map.removeLayer(marker);
            } else if (data.status === 'duplicate') {
                alert(`ℹ️ Notice: ${data.message}\nSeverity: ${data.severity} at ${data.area}`);
            } else {
                alert("❌ AI Error: " + data.message);
            }
        } catch (error) {
            console.error(error);
            alert("❌ Connection Error: Ensure app.py is running in your terminal!");
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerText = "🚀 Submit for AI Analysis";
        }
    });

    function displayUserStatus() {
        const list = document.getElementById('userStatusList');
        if (!list) return;
        const reports = JSON.parse(localStorage.getItem('safepath_reports') || '[]');
        if (reports.length === 0) return;
        list.innerHTML = ''; 
        reports.slice().reverse().forEach(r => {
            const card = document.createElement('div');
            card.className = "status-card status-pending";
            card.style.background = "white";
            card.style.padding = "15px";
            card.style.margin = "10px 0";
            card.style.borderRadius = "10px";
            card.style.borderLeft = "5px solid #e67e22";
            card.innerHTML = `<strong>📍 ${r.area || 'Detected Location'} (${r.severity})</strong><br>Status: ${r.status}`;
            list.appendChild(card);
        });
    }

    function updateImpactCounter() {
        const reports = JSON.parse(localStorage.getItem('safepath_reports') || '[]');
        const fixed = reports.filter(r => r.status === 'Fixed' || r.status === 'Repaired').length;
        if(document.getElementById('citizenTotal')) document.getElementById('citizenTotal').innerText = reports.length;
        if(document.getElementById('citizenFixed')) document.getElementById('citizenFixed').innerText = fixed;
    }

    displayUserStatus();
    updateImpactCounter();
});