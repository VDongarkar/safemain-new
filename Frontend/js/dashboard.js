document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Map - Centered on Pune/PCMC
    const map = L.map('dashMap').setView([18.6298, 73.7997], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
    let markers = [];
    let currentSearchTerm = ""; 
    let allLiveReports = []; // Holds the live backend data globally

    // 2. Live Status Update: Connects directly to Flask Backend
    window.updateStatus = async (id) => {
        try {
            const response = await fetch('http://localhost:5000/api/reports/update-status', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: id, status: 'Repaired' })
            });
            const data = await response.json();
            if (data.status === 'success') {
                alert("Pothole marked as Fixed and citizen notified!");
                fetchAndLoadDashboard(); // Refresh directly from SQLite
            } else {
                alert("Error updating status: " + data.message);
            }
        } catch (error) {
            console.error(error);
            alert("Connection error to pipeline server stream.");
        }
    };

    // 3. Helper: Copy Coordinates
    window.copyCoords = (lat, lng) => {
        navigator.clipboard.writeText(`${lat}, ${lng}`);
        alert("Coordinates copied to clipboard!");
    };

    // 4. Filtering: Triggered by the search bar in dashboard.html
    window.filterByArea = (term) => {
        currentSearchTerm = term.toLowerCase();
        renderDashboardData(allLiveReports, currentSearchTerm);
    };

    // 5. Professional CSV Export using Live Data
    window.exportToCSV = () => {
        if (allLiveReports.length === 0) return alert("No reports available to export.");

        let csvContent = "data:text/csv;charset=utf-8,ID,Area,Severity,Reporter,Status,Date,Latitude,Longitude\n";
        allLiveReports.forEach(r => {
            const row = [r.id, `"${r.area || 'Unknown'}"`, r.severity, `"${r.reporter_name || 'Citizen'}"`, r.status, `"${r.timestamp}"`, r.latitude, r.longitude].join(",");
            csvContent += row + "\n";
        });

        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `SafePath_Full_Report_${new Date().toISOString().split('T')[0]}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    // 6. Summary Widgets
    function updateSummaryStats(filteredReports) {
        const totalEl = document.getElementById('totalReports');
        const highEl = document.getElementById('highSeverity');
        const resolvedEl = document.getElementById('resolvedReports');

        if(totalEl) totalEl.innerText = filteredReports.length;
        if(highEl) highEl.innerText = filteredReports.filter(r => r.severity === 'High').length;
        if(resolvedEl) resolvedEl.innerText = filteredReports.filter(r => r.status === 'Repaired' || r.status === 'Fixed').length;
    }

    // 7. Core Fetch Function from app.py SQLite Database
    async function fetchAndLoadDashboard() {
        try {
            const response = await fetch('http://localhost:5000/api/reports/all');
            const resData = await response.json();
            if (resData.status === 'success') {
                allLiveReports = resData.data; // Sync global array
                renderDashboardData(allLiveReports, currentSearchTerm);
            }
        } catch (error) {
            console.error("Failed fetching live backend reports:", error);
        }
    }

    // 8. Core Rendering Engine
    function renderDashboardData(reportsData, filter = "") {
        const container = document.getElementById('reports');
        if(!container) return;
        container.innerHTML = '';
        
        let reports = [...reportsData];

        // Filter by Area Name or Reporter Name from Backend Schema fields
        if (filter) {
            reports = reports.filter(r => 
                (r.area && r.area.toLowerCase().includes(filter)) || 
                (r.reporter_name && r.reporter_name.toLowerCase().includes(filter))
            );
        }

        updateSummaryStats(reports);

        // Clear Map
        markers.forEach(m => map.removeLayer(m));
        markers = [];

        // Render Cards & Map Markers
        reports.forEach(r => {
            // Fixed typo string syntax rule right here
            const gpsUrl = `https://www.google.com/maps?q=${r.latitude},${r.longitude}`;
            const imagePath = `http://localhost:5000${r.image_url}`;
            
            // Professional Color Palette
            const isFixed = (r.status === 'Repaired' || r.status === 'Fixed');
            const color = isFixed ? '#28a745' : (r.severity === 'High' ? '#d9534f' : '#f39c12');

            // Add Circle Marker to Map
            const m = L.circle([r.latitude, r.longitude], { 
                color: color, 
                fillColor: color, 
                fillOpacity: 0.5, 
                radius: 60 
            }).addTo(map).bindPopup(`
                <strong>${r.severity} Severity</strong><br>
                Area: ${r.area || 'Detected Location'}<br>
                <img src="${imagePath}" width="150px" style="border-radius:5px; margin: 5px 0;"/><br>
                <a href="${gpsUrl}" target="_blank" style="color:#3498db; font-weight:bold;">Open in Google Maps</a>
            `);
            markers.push(m);

            // Create Professional Card UI
            const card = document.createElement('div');
            card.className = 'report-item'; 
            card.style.cssText = `
                border-left: 6px solid ${color};
                padding: 20px;
                background: white;
                margin-bottom: 15px;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.04);
                display: flex;
                flex-direction: column;
                gap: 10px;
                transition: 0.3s;
            `;

            card.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <h4 style="margin:0; color: #2c3e50; font-size: 1.1rem;">📍 ${r.area || 'Unknown Region'}</h4>
                        <small style="color: #999;">${r.timestamp}</small>
                    </div>
                    <span style="background: ${color}22; color: ${color}; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: bold;">
                        ${r.severity}
                    </span>
                </div>
                
                <p style="margin:0; font-size: 0.9rem; color: #555;">
                    Reported by: <b>${r.reporter_name || 'Citizen'}</b> | Phone: <b>${r.reporter_phone}</b> | Status: <b>${r.status}</b>
                </p>

                <div style="display:flex; gap:10px; margin-top:10px;">
                    <a href="${gpsUrl}" target="_blank" class="btn small" style="background:#34a853; color:white; text-decoration:none; padding:8px 15px; border-radius:8px; font-size:0.8rem; font-weight: bold;">🧭 Navigate</a>
                    <button class="btn small" style="background:#edf2f7; color:#4a5568; border:none; padding:8px 15px; border-radius:8px; cursor:pointer; font-size:0.8rem;" onclick="copyCoords(${r.latitude}, ${r.longitude})">📋 Coords</button>
                    
                    ${!isFixed ? 
                        `<button class="btn small" style="background:#2c3e50; color:white; border:none; padding:8px 15px; border-radius:8px; cursor:pointer; font-size:0.8rem; font-weight: bold;" onclick="updateStatus(${r.id})">Mark Fixed</button>` 
                        : '<span style="color:#28a745; font-weight:bold; font-size: 0.85rem; display: flex; align-items: center;">✅ Resolved</span>'}
                </div>
            `;
            container.appendChild(card);
        });

        // Auto-pan to latest report if it exists
        if (reports.length > 0 && !filter) {
            map.panTo([reports[0].latitude, reports[0].longitude]);
        }
    }

    // Initial data fetch run on load
    fetchAndLoadDashboard();
});