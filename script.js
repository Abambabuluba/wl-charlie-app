/**
 * Base de Datos de Ejercicios
 * baseRm: Define de qué levantamiento se extrae el RM para calcular el peso.
 * pct: Porcentaje recomendado (ej. 0.85 = 85%).
 */
const database = {
    snatch: {
        despegue: [
            { nombre: "Deficit Snatch Deadlift", desc: "Mejora fuerza de salida.", baseRm: "snatch", pct: 1.10, series: "4 x 3" },
            { nombre: "Snatch Lift-off (Pausa rodilla)", desc: "Refuerza la postura.", baseRm: "snatch", pct: 0.90, series: "3 x 3" }
        ],
        transicion_lenta: [
            { nombre: "Snatch Balance", desc: "Velocidad bajo la barra.", baseRm: "snatch", pct: 0.85, series: "4 x 2" },
            { nombre: "Tall Snatch", desc: "Aisla la tracción debajo.", baseRm: "snatch", pct: 0.50, series: "4 x 3" }
        ],
        recepcion_inestable: [
            { nombre: "Overhead Squat con pausa", desc: "Estabilidad abajo (3s).", baseRm: "ohs", pct: 0.80, series: "4 x 2" },
            { nombre: "Snatch Push Press", desc: "Bloqueo de hombros.", baseRm: "snatch", pct: 0.90, series: "3 x 4" }
        ]
    },
    clean: {
        barra_choca: [
            { nombre: "Muscle Clean", desc: "Rotación activa de codos.", baseRm: "clean", pct: 0.50, series: "3 x 3" },
            { nombre: "Tall Clean", desc: "Transición sin inercia.", baseRm: "clean", pct: 0.60, series: "4 x 3" }
        ],
        caida_sentadilla: [
            { nombre: "Front Squat con pausa", desc: "Fuerza en el agujero.", baseRm: "fs", pct: 0.80, series: "4 x 3" },
            { nombre: "Clean Deadlift", desc: "Postura de tirón.", baseRm: "clean", pct: 1.10, series: "4 x 4" }
        ]
    },
    jerk: {
        empuje_flojo: [
            { nombre: "Push Press", desc: "Conexión piernas-brazos.", baseRm: "jerk", pct: 0.80, series: "4 x 4" },
            { nombre: "Jerk Dip Squats", desc: "Sobrecarga en la frenada.", baseRm: "jerk", pct: 1.15, series: "4 x 3" }
        ],
        inestabilidad_split: [
            { nombre: "Press in Split", desc: "Aísla el equilibrio del split.", baseRm: "press", pct: 0.60, series: "3 x 5" },
            { nombre: "Jerk Balance", desc: "Reparto de pesos pie-pie.", baseRm: "jerk", pct: 0.65, series: "4 x 3" }
        ]
    }
};

const labels = {
    snatch: { despegue: "Falla en el despegue", transicion_lenta: "Lentitud al meterse debajo", recepcion_inestable: "Inestabilidad en recepción" },
    clean: { barra_choca: "La barra choca / se aleja", caida_sentadilla: "Caída pesada / aplastamiento" },
    jerk: { empuje_flojo: "Empuje flojo (Dip/Drive)", inestabilidad_split: "Inestabilidad en el split" }
};

const liftSelect = document.getElementById('lift-select');
const weaknessSelect = document.getElementById('weakness-select');

// --- INICIO NUEVO CÓDIGO AUTO-GUARDADO ---
const rmInputs = ['rm-snatch', 'rm-clean', 'rm-jerk', 'rm-bs', 'rm-fs', 'rm-dl', 'rm-press', 'rm-ohs'];

// 1. Cargar datos guardados al iniciar
rmInputs.forEach(id => {
    const savedValue = localStorage.getItem(id);
    if (savedValue !== null) {
        document.getElementById(id).value = savedValue;
    }
    
    // 2. Guardar datos cada vez que el usuario cambie un número
    document.getElementById(id).addEventListener('input', (e) => {
        localStorage.setItem(id, e.target.value);
    });
});
// --- FIN NUEVO CÓDIGO AUTO-GUARDADO ---

liftSelect.addEventListener('change', (e) => {
    const lift = e.target.value;
    weaknessSelect.innerHTML = '<option value="" disabled selected>-- Selecciona --</option>';
    weaknessSelect.disabled = false;
    for (const key in labels[lift]) {
        weaknessSelect.innerHTML += `<option value="${key}">${labels[lift][key]}</option>`;
    }
});

document.getElementById('generate-btn').addEventListener('click', () => {
    if (!liftSelect.value || !weaknessSelect.value) return alert("Selecciona levantamiento y fallo.");

    // Recoger RMs del usuario
    const rms = {
        snatch: parseFloat(document.getElementById('rm-snatch').value) || 0,
        clean: parseFloat(document.getElementById('rm-clean').value) || 0,
        jerk: parseFloat(document.getElementById('rm-jerk').value) || 0,
        bs: parseFloat(document.getElementById('rm-bs').value) || 0,
        fs: parseFloat(document.getElementById('rm-fs').value) || 0,
        dl: parseFloat(document.getElementById('rm-dl').value) || 0,
        press: parseFloat(document.getElementById('rm-press').value) || 0,
        ohs: parseFloat(document.getElementById('rm-ohs').value) || 0,
    };

    // 1. MOTOR DE DIAGNÓSTICO
    let diagHTML = "";
    
    // Análisis Clean vs Squats
    const ratioCleanFS = rms.clean / rms.fs;
    if (ratioCleanFS >= 0.90) diagHTML += `<div class="diagnostic-text">⚠️ <b>Clean vs Front Squat:</b> Tu Clean (${rms.clean}kg) es el ${(ratioCleanFS*100).toFixed(0)}% de tu Front Squat (${rms.fs}kg). Específicamente, una eficiencia superior al 85-90% indica que tu técnica es excelente, pero estás severamente limitado por la fuerza de tus piernas. ¡Toca subir esa sentadilla frontal!</div>`;
    else if ((rms.clean / rms.bs) < 0.60) diagHTML += `<div class="diagnostic-text">💡 <b>Fuga de técnica en Clean:</b> Tienes fuerza de sobra en piernas (BS ${rms.bs}kg), el Clean debería subir fácil.</div>`;

    // Análisis Jerk vs Press
    const ratioJerkPress = rms.jerk / rms.press;
    if (ratioJerkPress < 1.3) diagHTML += `<div class="diagnostic-text">⚠️ <b>Jerk vs Strict Press:</b> Tu Jerk (${rms.jerk}kg) es solo ${ratioJerkPress.toFixed(1)}x tu Press (${rms.press}kg). Con esos hombros, deberías rondar los 95-100kg de Jerk. El problema está casi seguro en la potencia de tus piernas durante el 'dip & drive' o en el timing del Split, no en la fuerza de empuje.</div>`;

    // Análisis Snatch vs OHS
    if (rms.snatch >= rms.ohs && rms.ohs > 0) diagHTML += `<div class="diagnostic-text">⚠️ <b>Snatch vs OHS:</b> Tu limitante absoluto es la fuerza/estabilidad de los hombros y core. No vas a poder arrancar más de lo que puedas sostener en OHS (${rms.ohs}kg).</div>`;

    const diagBox = document.getElementById('diagnostic-box');
    if (diagHTML === "") {
        diagBox.style.display = 'none';
    } else {
        diagBox.style.display = 'block';
        document.getElementById('diagnostic-content').innerHTML = diagHTML;
    }

    // 2. GENERAR LISTA DE EJERCICIOS (Resumen)
    const ejList = database[liftSelect.value][weaknessSelect.value];
    const listContainer = document.getElementById('exercise-list');
    listContainer.innerHTML = '';

    ejList.forEach(ej => {
        const baseWeight = rms[ej.baseRm];
        const targetWeight = baseWeight > 0 ? Math.round(baseWeight * ej.pct) : "- ";
        const percentText = (ej.pct * 100).toFixed(0);

        listContainer.innerHTML += `
            <div class="accessory-card">
                <div class="accessory-info">
                    <div class="accessory-title">${ej.nombre}</div>
                    <div class="accessory-desc">${ej.desc}</div>
                </div>
                <div class="prescription">
                    <div class="prescription-sets">${ej.series}</div>
                    <div class="prescription-weight">${targetWeight} kg <span style="font-size:0.7rem; color:#aaa; font-weight:normal;">(${percentText}% del RM)</span></div>
                </div>
            </div>
        `;
    });

    // 3. GENERAR PIZARRA (4 SEMANAS CHARLIE)
    const weeksContainer = document.getElementById('weeks-container');
    weeksContainer.innerHTML = '';

    let csvContent = "\uFEFFRUTINA CHARLIE - PLAN DE 4 SEMANAS\n";

    const weeks = [
        { title: "Week 1 - Base Volume", pctBase: 0.75, intensity: "LIGHT" },
        { title: "Week 2 - Medium Load", pctBase: 0.80, intensity: "MEDIUM" },
        { title: "Week 3 - Heavy Peak", pctBase: 0.88, intensity: "HEAVY" },
        { title: "Week 4 - Deload", pctBase: 0.65, intensity: "LIGHT" }
    ];

    weeks.forEach(week => {
        const wHangSnatch = Math.round(rms.snatch * week.pctBase) || "-";
        const wSnatchBal = Math.round(rms.snatch * (week.pctBase - 0.05)) || "-";
        const wMuscleSnatch = Math.round(rms.snatch * (week.pctBase - 0.20)) || "-";

        const wHangCJ = Math.round(rms.jerk * week.pctBase) || "-";
        const wTallClean = Math.round(rms.clean * (week.pctBase - 0.25)) || "-";
        
        const wPushPress = Math.round(rms.jerk * (week.pctBase - 0.10)) || "-";
        const wTallJerk = Math.round(rms.jerk * (week.pctBase - 0.25)) || "-";
        const wFrontRack = Math.round(rms.clean * 1.15) || "-";

        // Formato limpio en CSV por semanas
        csvContent += `\n=========================================\n`;
        csvContent += `${week.title.toUpperCase()}\n`;
        csvContent += `=========================================\n`;

        let html = `
        <div class="week-container">
            <div class="week-header" onclick="const grid = this.nextElementSibling; grid.classList.toggle('hidden'); const icon = this.querySelector('.toggle-icon'); icon.style.transform = grid.classList.contains('hidden') ? 'rotate(-90deg)' : 'rotate(0deg)';">
                <h3 class="week-title">${week.title}</h3>
                <span class="toggle-icon">▼</span>
            </div>
            <div class="sessions-grid">
        `;

        const renderEj = (sessionHeader, name, reps, weight, intensity, isCorrective = false) => {
            let badge = intensity ? `<span class="intensity-badge intensity-${intensity.toLowerCase()}">${intensity}</span>` : "";
            let classC = isCorrective ? "corrective-highlight" : "";
            
            // Si hay cabecera de sesión, la añadimos al CSV
            if (sessionHeader) {
                csvContent += `\n--- ${sessionHeader} ---\n`;
                csvContent += `Ejercicio;Series;Peso;Intensidad\n`;
            }
            
            // Añadir fila de ejercicio al CSV
            const csvWeight = weight !== "-" ? weight + " kg" : "-";
            const cleanName = name.replace("★ ", ">> ");
            csvContent += `"${cleanName}";"${reps}";"${csvWeight}";"${intensity}"\n`;

            return `
            <div class="exercise-item ${classC}">
                <div class="exercise-icon"></div>
                <div class="exercise-details">
                    <div class="exercise-name">${name}</div>
                    <div class="exercise-prescription">
                        <span>${reps}</span>
                        <div>${weight !== "-" ? weight + " kg" : ""} ${badge}</div>
                    </div>
                </div>
            </div>
            `;
        };

        const renderCorrective = (index) => {
            if(ejList[index]) {
                const ej = ejList[index];
                const baseWeight = rms[ej.baseRm] || 0;
                const adjustedPct = week.pctBase < 0.7 ? ej.pct * 0.8 : ej.pct; 
                const targetWeight = baseWeight > 0 ? Math.round(baseWeight * adjustedPct) : "-";
                return renderEj(null, `★ ${ej.nombre}`, ej.series, targetWeight, week.intensity, true);
            }
            return "";
        };

        // Session 1: Snatch Tech
        html += `
        <div class="sticky-note">
            <div class="pin"></div>
            <div class="session-title">Session 1</div>
            ${renderEj("SESIÓN 1", "Muscle Snatch + OHS", "3 sets x 3+3 reps", wMuscleSnatch, "LIGHT")}
            ${renderEj(null, "Hang Snatch (B. Knee)", "5 sets x 2 reps", wHangSnatch, week.intensity)}
            ${renderEj(null, "Snatch Balance", "4 sets x 2 reps", wSnatchBal, "MEDIUM")}
            ${(liftSelect.value === 'snatch' || liftSelect.value === 'clean') ? renderCorrective(0) : ""}
        </div>
        `;

        // Session 2: Jerk & Overhead Tech
        html += `
        <div class="sticky-note">
            <div class="pin"></div>
            <div class="session-title">Session 2</div>
            ${renderEj("SESIÓN 2", "Tall Jerk", "4 sets x 3 reps", wTallJerk, "LIGHT")}
            ${renderEj(null, "Push Press + Power Jerk", "4 sets x 2+2 reps", wPushPress, week.intensity)}
            ${liftSelect.value === 'jerk' ? renderCorrective(0) : ""}
            ${liftSelect.value === 'snatch' ? renderCorrective(1) : ""}
        </div>
        `;

        // Session 3: Clean Tech & Core
        html += `
        <div class="sticky-note">
            <div class="pin"></div>
            <div class="session-title">Session 3</div>
            ${renderEj("SESIÓN 3", "Tall Clean", "3 sets x 3 reps", wTallClean, "LIGHT")}
            ${renderEj(null, "Hang Clean + Jerk", "5 sets x 2+1 reps", wHangCJ, week.intensity)}
            ${renderEj(null, "Front Rack Hold", "3 sets x 10 sec", wFrontRack, "HEAVY")}
            ${(liftSelect.value === 'clean' || liftSelect.value === 'jerk') ? renderCorrective(1) : ""}
        </div>
        `;

        html += `</div></div>`;
        weeksContainer.innerHTML += html;
    });

    const downloadBtn = document.getElementById('download-csv-btn');
    if (downloadBtn) {
        downloadBtn.onclick = () => {
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.setAttribute("href", url);
            link.setAttribute("download", "Rutina_Charlie_WL.csv");
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        };
    }

    document.getElementById('routine-board').style.display = 'block';
    document.getElementById('results-container').style.display = 'block';
});
