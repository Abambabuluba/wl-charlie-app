/**
 * Base de Datos de Ejercicios
 */
const database = {
    snatch: {
        despegue: [
            { nombre: "Deficit Snatch Deadlift", desc: "Mejora fuerza de salida.", baseRm: "snatch", pct: 1.10, series: "3 x 3" },
            { nombre: "Snatch Lift-off (Pausa rodilla)", desc: "Refuerza la postura.", baseRm: "snatch", pct: 0.90, series: "3 x 2" },
            { nombre: "Snatch Pull con pausa", desc: "Control en la tracción.", baseRm: "snatch", pct: 1.05, series: "3 x 3" },
            { nombre: "Segment Snatch Pull", desc: "Pausa en rodilla y cadera.", baseRm: "snatch", pct: 1.00, series: "3 x 2" },
            { nombre: "Halting Snatch Deadlift", desc: "Isometría al nivel del ombligo.", baseRm: "snatch", pct: 1.05, series: "3 x 3" }
        ],
        transicion_lenta: [
            { nombre: "Snatch Balance", desc: "Velocidad bajo la barra.", baseRm: "snatch", pct: 0.85, series: "3 x 2" },
            { nombre: "Tall Snatch", desc: "Aisla la tracción debajo.", baseRm: "snatch", pct: 0.50, series: "2 x 3" },
            { nombre: "Hang Snatch (High Hang)", desc: "Aceleración final.", baseRm: "snatch", pct: 0.70, series: "3 x 2" },
            { nombre: "Drop Snatch", desc: "Caída brusca sin impulso.", baseRm: "snatch", pct: 0.60, series: "3 x 2" },
            { nombre: "Hip Snatch", desc: "Desde el bolsillo.", baseRm: "snatch", pct: 0.65, series: "3 x 2" }
        ],
        recepcion_inestable: [
            { nombre: "Overhead Squat con pausa", desc: "Estabilidad abajo (3s).", baseRm: "ohs", pct: 0.80, series: "3 x 2" },
            { nombre: "Snatch Push Press", desc: "Bloqueo de hombros.", baseRm: "snatch", pct: 0.90, series: "3 x 3" },
            { nombre: "Heaving Snatch Balance", desc: "Velocidad y fijación.", baseRm: "snatch", pct: 0.95, series: "3 x 2" },
            { nombre: "Sots Press (Snatch)", desc: "Movilidad de hombro.", baseRm: "press", pct: 0.40, series: "3 x 5" },
            { nombre: "Snatch Balance sin dip", desc: "Empuje estricto abajo.", baseRm: "snatch", pct: 0.50, series: "3 x 3" }
        ]
    },
    clean: {
        barra_choca: [
            { nombre: "Muscle Clean", desc: "Rotación activa de codos.", baseRm: "clean", pct: 0.50, series: "2 x 3" },
            { nombre: "Tall Clean", desc: "Transición sin inercia.", baseRm: "clean", pct: 0.60, series: "2 x 3" },
            { nombre: "Clean High Pull", desc: "Extensión completa.", baseRm: "clean", pct: 1.05, series: "3 x 3" },
            { nombre: "Clean Power Position", desc: "Verticalidad pura.", baseRm: "clean", pct: 0.65, series: "3 x 2" },
            { nombre: "Clean Pull al ombligo", desc: "Contacto sin meterse.", baseRm: "clean", pct: 1.10, series: "3 x 3" }
        ],
        caida_sentadilla: [
            { nombre: "Front Squat con pausa", desc: "Fuerza en el agujero.", baseRm: "fs", pct: 0.80, series: "3 x 2" },
            { nombre: "Clean Deadlift", desc: "Postura de tirón.", baseRm: "clean", pct: 1.10, series: "3 x 3" },
            { nombre: "Tempo Front Squat", desc: "Control excéntrico.", baseRm: "fs", pct: 0.75, series: "2 x 3" },
            { nombre: "1 y 1/4 Front Squat", desc: "Rebote consciente.", baseRm: "fs", pct: 0.70, series: "3 x 3" },
            { nombre: "Pull a rodilla + Clean", desc: "Control postural.", baseRm: "clean", pct: 0.85, series: "3 x 1+1" }
        ]
    },
    jerk: {
        empuje_flojo: [
            { nombre: "Push Press", desc: "Conexión piernas-brazos.", baseRm: "jerk", pct: 0.80, series: "3 x 3" },
            { nombre: "Jerk Dip Squats", desc: "Sobrecarga en la frenada.", baseRm: "jerk", pct: 1.15, series: "3 x 3" },
            { nombre: "Push Press con pausa", desc: "Fuerza elástica.", baseRm: "jerk", pct: 0.75, series: "3 x 3" },
            { nombre: "Push Press Continuo", desc: "Rebote explosivo.", baseRm: "jerk", pct: 0.70, series: "3 x 4" },
            { nombre: "Jerk Dip Holds", desc: "Aguantar dip pesado.", baseRm: "jerk", pct: 1.20, series: "3 x 10s" }
        ],
        inestabilidad_split: [
            { nombre: "Press in Split", desc: "Aísla equilibrio split.", baseRm: "press", pct: 0.60, series: "2 x 5" },
            { nombre: "Jerk Balance", desc: "Reparto de pesos.", baseRm: "jerk", pct: 0.65, series: "3 x 3" },
            { nombre: "Split Squat Isométrico", desc: "Estabilidad en tijera.", baseRm: "bs", pct: 0.30, series: "2 x 20s" },
            { nombre: "Split Squat Búlgaro", desc: "Fuerza unilateral.", baseRm: "bs", pct: 0.25, series: "3 x 6" },
            { nombre: "Drop to Split", desc: "Velocidad de pies.", baseRm: "jerk", pct: 0.30, series: "3 x 3" }
        ]
    }
};

const labels = {
    snatch: { despegue: "Falla en el despegue", transicion_lenta: "Lentitud al meterse debajo", recepcion_inestable: "Inestabilidad en recepción" },
    clean: { barra_choca: "La barra choca / se aleja", caida_sentadilla: "Caída pesada / aplastamiento" },
    jerk: { empuje_flojo: "Empuje flojo (Dip/Drive)", inestabilidad_split: "Inestabilidad en el split" }
};

const rmInputs = ['rm-snatch', 'rm-clean', 'rm-jerk', 'rm-bs', 'rm-fs', 'rm-dl', 'rm-press', 'rm-ohs'];
const athleteInputs = ['bw-input', 'gender-input'];

let radarChartInst = null;

// Inicialización de Eventos y Carga de Datos
window.addEventListener('DOMContentLoaded', () => {
    // Cargar RMs
    rmInputs.forEach(id => {
        const savedValue = localStorage.getItem(id);
        if (savedValue !== null) document.getElementById(id).value = savedValue;
        document.getElementById(id).addEventListener('input', (e) => {
            localStorage.setItem(id, e.target.value);
            updateDiagnostics();
        });
    });

    // Cargar Atleta
    athleteInputs.forEach(id => {
        const savedValue = localStorage.getItem(id);
        if (savedValue !== null) document.getElementById(id).value = savedValue;
        document.getElementById(id).addEventListener('input', (e) => {
            localStorage.setItem(id, e.target.value);
            updateDiagnostics();
        });
    });

    // Eventos Selectores de Debilidad
    const liftSelect = document.getElementById('lift-select');
    const weaknessSelect = document.getElementById('weakness-select');
    liftSelect.addEventListener('change', (e) => {
        const lift = e.target.value;
        weaknessSelect.innerHTML = '<option value="" disabled selected>-- Selecciona --</option>';
        weaknessSelect.disabled = false;
        for (const key in labels[lift]) {
            weaknessSelect.innerHTML += `<option value="${key}">${labels[lift][key]}</option>`;
        }
        // Limpiar pizarra si cambia de levantamiento
        document.getElementById('exercise-list').innerHTML = '';
        document.getElementById('weeks-container').innerHTML = '';
        document.getElementById('routine-board').style.display = 'none';
    });

    weaknessSelect.addEventListener('change', () => {
        generateRoutine();
    });

    // Modal Calculadora 1RM
    initModal();

    // Primera carga
    updateDiagnostics();
});

// MOTOR DE DIAGNÓSTICO EN TIEMPO REAL
function updateDiagnostics() {
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
    
    const bw = parseFloat(document.getElementById('bw-input').value) || 1;
    const gender = document.getElementById('gender-input').value;

    const cj = Math.min(rms.clean, rms.jerk) || rms.clean || rms.jerk; 

    // 1. SINCLAIR & TOTAL
    const total = rms.snatch + cj;
    document.getElementById('total-val').innerHTML = `${total} <small>kg</small>`;
    
    let A = gender === 'M' ? 0.751945030 : 0.783497476;
    let b = gender === 'M' ? 175.508 : 153.655;
    let SC = 1;
    if (bw <= b) {
        let X = Math.log10(bw / b);
        SC = Math.pow(10, A * Math.pow(X, 2));
    }
    const sinclair = total * SC;
    
    // Animación de contador para el Sinclair
    const currentSinclair = parseFloat(document.getElementById('sinclair-val').innerText) || 0;
    animateValue('sinclair-val', currentSinclair, sinclair, 800);

    // 2. ALERTAS DIAGNÓSTICO
    let diagHTML = "";

    if (rms.bs > 0) {
        const ratioFSBS = rms.fs / rms.bs;
        if (ratioFSBS < 0.75) diagHTML += `<div class="diagnostic-text">⚠️ <b>Front Squat vs Back Squat (${(ratioFSBS*100).toFixed(0)}%):</b> Ideal 85-90%. Falta fuerza en los cuádriceps, debilidad en la zona media (core) o falta de movilidad para mantener el torso erguido.</div>`;
    }
    if (rms.jerk > 0) {
        const ratioPressJerk = rms.press / rms.jerk;
        if (ratioPressJerk < 0.35) diagHTML += `<div class="diagnostic-text">⚠️ <b>Strict Press vs Jerk (${(ratioPressJerk*100).toFixed(0)}%):</b> Ideal 45-50%. Tu fuerza estricta de hombros es deficiente respecto al Jerk.</div>`;
        else if (ratioPressJerk > 0.60) diagHTML += `<div class="diagnostic-text">💡 <b>Strict Press vs Jerk (${(ratioPressJerk*100).toFixed(0)}%):</b> Tienes fuerza estricta sobrante pero tu Jerk no lo refleja. Suele haber un fallo en el timing o en la potencia de piernas (dip & drive).</div>`;
    }
    if (rms.bs > 0) {
        const ratioCleanBS = rms.clean / rms.bs;
        if (ratioCleanBS < 0.65) diagHTML += `<div class="diagnostic-text">⚠️ <b>Clean vs Back Squat (${(ratioCleanBS*100).toFixed(0)}%):</b> Ideal 75-80%. Fuga de técnica en Clean: tienes fuerza de sobra en piernas, el Clean debería subir mucho más fácil.</div>`;
    }
    if (rms.fs > 0 && cj > 0) {
        const ratioCJFS = cj / rms.fs;
        if (ratioCJFS >= 0.90) diagHTML += `<div class="diagnostic-text">🌟 <b>Clean&Jerk vs Front Squat (${(ratioCJFS*100).toFixed(0)}%):</b> Si estás por encima del 90%: Eres muy eficiente técnicamente, pero tu límite actual es la fuerza pura de pierna. Necesitas subir tus sentadillas.</div>`;
        else if (ratioCJFS < 0.75) diagHTML += `<div class="diagnostic-text">⚠️ <b>Clean&Jerk vs Front Squat (${(ratioCJFS*100).toFixed(0)}%):</b> Ideal 85-90%. Tu eficiencia en los movimientos olímpicos es muy baja en proporción a tu fuerza de sentadilla frontal.</div>`;
    }
    if (rms.bs > 0) {
        const ratioSnatchBS = rms.snatch / rms.bs;
        if (ratioSnatchBS < 0.50) diagHTML += `<div class="diagnostic-text">⚠️ <b>Snatch vs Back Squat (${(ratioSnatchBS*100).toFixed(0)}%):</b> Ideal 60-65%. Tu arranque está sufriendo mucho por un tema técnico o de movilidad, dadas las sentadillas que manejas.</div>`;
    }
    if (cj > 0) {
        const ratioSnatchCJ = rms.snatch / cj;
        if (ratioSnatchCJ < 0.70) diagHTML += `<div class="diagnostic-text">⚠️ <b>Snatch vs Clean&Jerk (${(ratioSnatchCJ*100).toFixed(0)}%):</b> Ideal 80-85%. Si el Snatch es muy bajo en proporción: Suele indicar miedo a meterse debajo de la barra o falta de técnica/movilidad, ya que el C&J requiere más fuerza bruta.</div>`;
    }
    if (rms.clean > 0 && rms.jerk > 0) {
        const ratioJerkClean = rms.jerk / rms.clean;
        if (rms.clean > rms.jerk) diagHTML += `<div class="diagnostic-text">⚠️ <b>Jerk vs Clean (${(ratioJerkClean*100).toFixed(0)}%):</b> Ideal 100-105%. Si tu Clean es mayor que tu Jerk, el fallo está en la técnica del empuje, en el dip & drive, o en la fuerza de hombros/tríceps.</div>`;
    }
    if (rms.snatch > 0 && rms.ohs > 0) {
        const ratioOHSSnatch = rms.ohs / rms.snatch;
        if (rms.ohs <= rms.snatch) diagHTML += `<div class="diagnostic-text">⚠️ <b>OHS vs Snatch (${(ratioOHSSnatch*100).toFixed(0)}%):</b> Ideal 105-110%. Si el OHS es igual o menor a tu Snatch, tu cuello de botella es la estabilidad de los hombros o el core bajo carga.</div>`;
    }
    if (diagHTML === "") {
        diagHTML = `<div class="diagnostic-text">✅ <b>Todo equilibrado:</b> Tus ratios están dentro de los márgenes óptimos (sin desfases mayores al 10%). ¡Estás haciendo un gran trabajo!</div>`;
    }

    // --- RECOMENDACIÓN INTELIGENTE DE RUTINA ---
    let recLift = "";
    let recWeakness = "";
    let worstDeviation = 0; 

    const checkDeviation = (ratio, ideal, lift, weakness, isReverse = false) => {
        let deviation = isReverse ? (ratio - ideal)/ideal : (ideal - ratio)/ideal;
        if (deviation > worstDeviation && deviation > 0.05) { // Desfase > 5% para recomendar
            worstDeviation = deviation;
            recLift = lift;
            recWeakness = weakness;
        }
    };

    if (rms.bs > 0) checkDeviation(rms.snatch / rms.bs, 0.62, 'snatch', 'despegue');
    if (cj > 0) checkDeviation(rms.snatch / cj, 0.82, 'snatch', 'transicion_lenta');
    if (rms.snatch > 0) checkDeviation(rms.ohs / rms.snatch, 1.08, 'snatch', 'recepcion_inestable');
    if (rms.bs > 0) checkDeviation(rms.clean / rms.bs, 0.78, 'clean', 'caida_sentadilla');
    if (rms.clean > 0) checkDeviation(rms.jerk / rms.clean, 1.02, 'jerk', 'empuje_flojo');
    if (rms.jerk > 0) checkDeviation(rms.press / rms.jerk, 0.45, 'jerk', 'empuje_flojo', true);

    if (recLift !== "") {
        const liftName = recLift.charAt(0).toUpperCase() + recLift.slice(1);
        const weakName = labels[recLift][recWeakness];
        
        diagHTML = `
        <div class="diagnostic-text" style="background: rgba(0, 229, 255, 0.1); border: 1px solid var(--primary); padding: 1.2rem; border-radius: 10px; margin-bottom: 1.5rem;">
            🤖 <b>Recomendación Automática:</b> Basado en tus debilidades matemáticas, te sugerimos enfocarte en <b>${liftName} - ${weakName}</b>. 
            <button onclick="applyRecommendation('${recLift}', '${recWeakness}')" class="btn" style="padding: 0.8rem; margin-top: 1rem; background: var(--primary); color:#000; font-size: 1rem;">Seleccionar y Generar Rutina</button>
        </div>
        ` + diagHTML;
    }

    document.getElementById('diagnostic-content').innerHTML = diagHTML;

    // 3. ACTUALIZAR RADAR CHART
    updateRadarChart(rms);

    // 4. ACTUALIZAR RUTINA (si hay fallo seleccionado)
    const liftSelect = document.getElementById('lift-select');
    const weaknessSelect = document.getElementById('weakness-select');
    if (liftSelect.value && weaknessSelect.value) {
        generateRoutine();
    }
}

// RADAR CHART
function updateRadarChart(rms) {
    const ctx = document.getElementById('radarChart').getContext('2d');
    
    // Normalizar respecto a Back Squat u otra métrica si bs es 0.
    const base = rms.bs > 0 ? rms.bs : 100;
    
    // Ratios ideales respecto al BS (aprox)
    const idealRatios = {
        bs: 1.0,
        fs: 0.85,
        dl: 1.10,
        snatch: 0.62,
        clean: 0.78,
        jerk: 0.78,
        ohs: 0.65,
        press: 0.38
    };

    // Calculamos el % de eficiencia. (Tu levantamiento / Levantamiento Ideal) * 100
    // Si levantas lo ideal, la puntuación es 100.
    const getScore = (lift, ratio) => {
        if (base === 0) return 0;
        const idealWeight = base * ratio;
        return idealWeight > 0 ? (rms[lift] / idealWeight) * 100 : 0;
    };

    const dataScores = [
        getScore('snatch', idealRatios.snatch),
        getScore('clean', idealRatios.clean),
        getScore('jerk', idealRatios.jerk),
        getScore('bs', idealRatios.bs),
        getScore('fs', idealRatios.fs),
        getScore('dl', idealRatios.dl),
        getScore('press', idealRatios.press),
        getScore('ohs', idealRatios.ohs)
    ];

    const data = {
        labels: ['Snatch', 'Clean', 'Jerk', 'B. Squat', 'F. Squat', 'Deadlift', 'Press', 'OHS'],
        datasets: [{
            label: 'Eficiencia vs Ideal (%)',
            data: dataScores,
            backgroundColor: 'rgba(0, 229, 255, 0.2)',
            borderColor: 'rgba(0, 229, 255, 1)',
            pointBackgroundColor: '#fff',
            pointBorderColor: 'rgba(0, 229, 255, 1)',
            pointHoverBackgroundColor: '#fff',
            pointHoverBorderColor: 'rgba(0, 229, 255, 1)',
            borderWidth: 2
        }, {
            // Línea Ideal del 100%
            label: 'Atleta Ideal',
            data: [100, 100, 100, 100, 100, 100, 100, 100],
            backgroundColor: 'transparent',
            borderColor: 'rgba(255, 42, 95, 0.5)',
            borderDash: [5, 5],
            pointRadius: 0,
            borderWidth: 2
        }]
    };

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            r: {
                angleLines: { color: 'rgba(255,255,255,0.1)' },
                grid: { color: 'rgba(255,255,255,0.1)' },
                pointLabels: { color: '#fff', font: { family: 'Outfit', size: 12 } },
                ticks: { display: false, min: 0, max: 130 }
            }
        },
        plugins: {
            legend: { labels: { color: '#fff', font: { family: 'Outfit' } } }
        }
    };

    if (radarChartInst) {
        radarChartInst.data = data;
        radarChartInst.update();
    } else {
        radarChartInst = new Chart(ctx, { type: 'radar', data: data, options: options });
    }
}

// MODAL CALCULADORA 1RM
function initModal() {
    const modal = document.getElementById('rm-modal');
    const closeBtn = document.getElementById('modal-close-btn');
    const applyBtn = document.getElementById('modal-apply-btn');
    let targetInputId = null;

    document.querySelectorAll('.magic-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            targetInputId = e.target.getAttribute('data-target');
            document.getElementById('modal-lift-name').innerText = targetInputId.replace('rm-', '').toUpperCase();
            document.getElementById('modal-weight').value = '';
            document.getElementById('modal-reps').value = '5';
            modal.style.display = 'flex';
        });
    });

    closeBtn.onclick = () => modal.style.display = 'none';

    applyBtn.onclick = () => {
        const w = parseFloat(document.getElementById('modal-weight').value);
        const r = parseFloat(document.getElementById('modal-reps').value);
        if (w > 0 && r > 0) {
            // Fórmula Epley: 1RM = Weight * (1 + Reps/30)
            const rmEpley = Math.round(w * (1 + r / 30));
            const targetInput = document.getElementById(targetInputId);
            targetInput.value = rmEpley;
            
            // Efecto Flash
            const inputWrap = targetInput.closest('.input-wrap');
            if (inputWrap) {
                inputWrap.classList.remove('flash-success');
                void inputWrap.offsetWidth; // trigger reflow
                inputWrap.classList.add('flash-success');
                setTimeout(() => inputWrap.classList.remove('flash-success'), 600);
            }
            
            // Forzar actualización
            localStorage.setItem(targetInputId, rmEpley);
            updateDiagnostics();
            modal.style.display = 'none';
        }
    };
}


// GENERACIÓN DE RUTINA (AUTOMÁTICA)
function generateRoutine() {
    const liftSelect = document.getElementById('lift-select');
    const weaknessSelect = document.getElementById('weakness-select');
    if (!liftSelect.value || !weaknessSelect.value) return;

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

    // 2. GENERAR LISTA DE EJERCICIOS (Resumen puntual)
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

    // 3. GENERAR PIZARRA (PLAN SEMANAL FIJO)
    const weeksContainer = document.getElementById('weeks-container');
    weeksContainer.innerHTML = '';

    const pctBase = 0.75; // Intensidad técnica fija para todo el bloque

    const wHangSnatch = Math.round(rms.snatch * pctBase) || "-";
    const wSnatchBal = Math.round(rms.snatch * (pctBase - 0.05)) || "-";
    const wMuscleSnatch = Math.round(rms.snatch * (pctBase - 0.20)) || "-";

    const wHangCJ = Math.round(rms.jerk * pctBase) || "-";
    const wTallClean = Math.round(rms.clean * (pctBase - 0.25)) || "-";
    
    const wPushPress = Math.round(rms.jerk * (pctBase - 0.10)) || "-";
    const wTallJerk = Math.round(rms.jerk * (pctBase - 0.25)) || "-";
    const wFrontRack = Math.round(rms.clean * 1.15) || "-";

    let html = `
    <div class="week-container">
        <div class="week-header">
            <h3 class="week-title">Rutina Semanal Fija (Repetir como calentamiento)</h3>
            <span class="toggle-icon" style="display:none;"></span>
        </div>
        <div class="sessions-grid">
    `;

    const renderEj = (sessionHeader, name, reps, weight, intensity, isCorrective = false, extraHtml = "") => {
        let badge = intensity ? `<span class="intensity-badge intensity-${intensity.toLowerCase()}">${intensity}</span>` : "";
        let classC = isCorrective ? "corrective-highlight" : "";
        return `
        <div class="exercise-item ${classC}">
            <div class="exercise-icon"></div>
            <div class="exercise-details">
                <div class="exercise-name">${name} ${extraHtml}</div>
                <div class="exercise-prescription">
                    <span class="series-display">${reps}</span>
                    <div><span class="weight-display">${weight !== "-" ? weight + " kg" : "-"}</span> ${badge}</div>
                </div>
            </div>
        </div>
        `;
    };

    const renderCorrective = (index) => {
        if(ejList[index]) {
            const ej = ejList[index];
            const baseWeight = rms[ej.baseRm] || 0;
            const targetWeight = baseWeight > 0 ? Math.round(baseWeight * ej.pct) : "-";
            const btnHtml = `<button title="Cambiar Ejercicio alternativo" onclick="reRollExercise(this, '${liftSelect.value}', '${weaknessSelect.value}', ${index})" class="reroll-btn">🔄</button>`;
            const nameHtml = `<span class="corr-name">★ ${ej.nombre}</span>`;
            return renderEj(null, nameHtml, ej.series, targetWeight, "TECH", true, btnHtml);
        }
        return "";
    };

    // Session 1: Snatch Tech
    html += `
    <div class="sticky-note">
        <div class="pin"></div>
        <div class="session-title">Sesión 1 (Día 1)</div>
        ${renderEj(null, "Muscle Snatch + OHS", "2 sets x 3+3 reps", wMuscleSnatch, "TECH")}
        ${renderEj(null, "Hang Snatch (B. Knee)", "3 sets x 2 reps", wHangSnatch, "TECH")}
        ${renderEj(null, "Snatch Balance", "2 sets x 2 reps", wSnatchBal, "TECH")}
        ${renderCorrective(0)}
    </div>
    `;

    // Session 2: Jerk & Overhead Tech
    html += `
    <div class="sticky-note">
        <div class="pin"></div>
        <div class="session-title">Sesión 2 (Día 2)</div>
        ${renderEj(null, "Tall Jerk", "2 sets x 3 reps", wTallJerk, "TECH")}
        ${renderEj(null, "Push Press + Power Jerk", "3 sets x 2+1 reps", wPushPress, "TECH")}
        ${renderCorrective(1)}
    </div>
    `;

    // Session 3: Clean Tech & Core
    html += `
    <div class="sticky-note">
        <div class="pin"></div>
        <div class="session-title">Sesión 3 (Día 3)</div>
        ${renderEj(null, "Tall Clean", "2 sets x 3 reps", wTallClean, "TECH")}
        ${renderEj(null, "Hang Clean + Jerk", "3 sets x 1+1 reps", wHangCJ, "TECH")}
        ${renderEj(null, "Front Rack Hold", "2 sets x 10 sec", wFrontRack, "HEAVY")}
        ${renderCorrective(2)}
    </div>
    `;

    html += `</div></div>`;
    weeksContainer.innerHTML += html;

    document.getElementById('routine-board').style.display = 'block';
    const btnDossier = document.getElementById('download-pdf-btn');
    if (btnDossier) btnDossier.style.display = 'inline-block';
}

// DESCARGA DE PDF (DOSSIER)
const downloadBtn = document.getElementById('download-pdf-btn');
if (downloadBtn) {
    downloadBtn.onclick = () => {
        const element = document.getElementById('dossier-export');
        
        // Aplicar modo PDF (Fondo blanco)
        element.classList.add('pdf-export-mode');
        
        // Cambiar colores del Radar a negro temporalmente
        if (radarChartInst) {
            radarChartInst.options.plugins.legend.labels.color = '#000';
            radarChartInst.options.scales.r.pointLabels.color = '#000';
            radarChartInst.options.scales.r.angleLines.color = 'rgba(0,0,0,0.1)';
            radarChartInst.options.scales.r.grid.color = 'rgba(0,0,0,0.1)';
            radarChartInst.update();
        }

        setTimeout(() => {
            downloadBtn.style.display = 'none';

            const opt = {
                margin:       10,
                filename:     'Dossier_Atleta_WL.pdf',
                image:        { type: 'jpeg', quality: 0.98 },
                html2canvas:  { scale: 2, useCORS: true, scrollY: 0 },
                jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' },
                pagebreak:    { mode: ['css', 'avoid-all'] }
            };

            html2pdf().set(opt).from(element).save().then(() => {
                downloadBtn.style.display = 'block';
                element.classList.remove('pdf-export-mode');
                // Restaurar radar
                if (radarChartInst) {
                    radarChartInst.options.plugins.legend.labels.color = '#fff';
                    radarChartInst.options.scales.r.pointLabels.color = '#fff';
                    radarChartInst.options.scales.r.angleLines.color = 'rgba(255,255,255,0.1)';
                    radarChartInst.options.scales.r.grid.color = 'rgba(255,255,255,0.1)';
                    radarChartInst.update();
                }
            });
        }, 300);
    };
}

// FUNCIÓN PARA ANIMAR NÚMEROS (CONTADOR)
function animateValue(id, start, end, duration) {
    if (start === end) return;
    const obj = document.getElementById(id);
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        obj.innerHTML = (progress * (end - start) + start).toFixed(1);
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}

// FUNCIÓN GLOBAL PARA APLICAR LA RECOMENDACIÓN INTELIGENTE
window.applyRecommendation = function(lift, weakness) {
    const liftSelect = document.getElementById('lift-select');
    const weaknessSelect = document.getElementById('weakness-select');
    
    liftSelect.value = lift;
    liftSelect.dispatchEvent(new Event('change'));
    
    weaknessSelect.value = weakness;
    weaknessSelect.dispatchEvent(new Event('change'));
    
    // Hacer scroll suave a la pizarra
    document.getElementById('routine-board').scrollIntoView({ behavior: 'smooth' });
};

// FUNCIÓN PARA CAMBIAR EJERCICIO CORRECTIVO (RE-ROLL)
window.reRollExercise = function(btn, lift, weakness, currIdx) {
    const arr = database[lift][weakness];
    if (!arr || arr.length <= 1) return;
    
    let newIdx;
    do {
        newIdx = Math.floor(Math.random() * arr.length);
    } while (newIdx === currIdx);
    
    // Actualizar onclick para evitar repetir en el siguiente clic
    btn.setAttribute("onclick", `reRollExercise(this, '${lift}', '${weakness}', ${newIdx})`);
    
    const ej = arr[newIdx];
    const item = btn.closest('.exercise-item');
    
    if (item) {
        // Efecto visual flash
        item.style.transition = '0.3s';
        item.style.backgroundColor = 'rgba(0, 229, 255, 0.4)';
        setTimeout(() => item.style.backgroundColor = '', 300);

        item.querySelector('.corr-name').innerText = `★ ${ej.nombre}`;
        item.querySelector('.series-display').innerText = ej.series;
        
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
        const baseWeight = rms[ej.baseRm] || 0;
        const targetWeight = baseWeight > 0 ? Math.round(baseWeight * ej.pct) : "-";
        
        const wDisplay = item.querySelector('.weight-display');
        if (wDisplay) wDisplay.innerText = targetWeight !== "-" ? `${targetWeight} kg` : "-";
    }
};
