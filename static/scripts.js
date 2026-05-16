function openModal() {
    document.getElementById('modal-empirica').style.display = 'flex';
}

function closeModal() {
    document.getElementById('modal-empirica').style.display = 'none';
}

function confirmPurchase() {
    const checkboxes = document.querySelectorAll('#modal-empirica input[type="checkbox"]');
    let selected = [];

    checkboxes.forEach(cb => {
        if (cb.checked) {
            selected.push(cb.value);
        }
    });

    if (selected.length > 0) {
        alert('Gracias por tu compra. Has seleccionado:\n' + selected.join(', '));
    } else {
        alert('Por favor selecciona al menos una opción.');
        return; // No cerrar el modal si no selecciona nada
    }

    closeModal();
}

function openModalGuiada() {
    document.getElementById('modal-guiada').style.display = 'flex';
}

function closeModalGuiada() {
    document.getElementById('modal-guiada').style.display = 'none';
}

function confirmPurchaseGuiada() {
    alert('Gracias por tu compra de la Ruta Guiada.');
    closeModalGuiada();
}


function openModalpdevida() {
    document.getElementById('modal-pdevida').style.display = 'flex';
}

function closeModalpdevida() {
    document.getElementById('modal-pdevida').style.display = 'none';
}

function confirmPurchasepdevida() {
    alert('Gracias por tu compra de la Ruta Propósito de Vida.');
    closeModalpdevida();
}


function openModalpdevidaguiada() {
    document.getElementById('modal-pdevidaguiada').style.display = 'flex';
}

function closeModalpdevidaguiada() {
    document.getElementById('modal-pdevidaguiada').style.display = 'none';
}

function confirmPurchasepdevidaguiada() {
    alert('Gracias por tu compra de la Ruta Propósito de Vida.');
    closeModalpdevidaguiada();
}

// Confesión y desahogo
function openModalConfesion() {
    document.getElementById('modal-confesion').style.display = 'flex';
}
function closeModalConfesion() {
    document.getElementById('modal-confesion').style.display = 'none';
}
function confirmPurchaseConfesion() {
    alert('Gracias por adquirir Confesión y desahogo.');
    closeModalConfesion();
}

// Coaching para mejorar tu cuerpo
function openModalCoaching() {
    document.getElementById('modal-coaching').style.display = 'flex';
}
function closeModalCoaching() {
    document.getElementById('modal-coaching').style.display = 'none';
}
function confirmPurchaseCoaching() {
    alert('Gracias por adquirir Coaching para mejorar tu cuerpo.');
    closeModalCoaching();
}

// Design thinking en tu vida
function openModalDesignThinking() {
    document.getElementById('modal-designthinking').style.display = 'flex';
}
function closeModalDesignThinking() {
    document.getElementById('modal-designthinking').style.display = 'none';
}
function confirmPurchaseDesignThinking() {
    alert('Gracias por adquirir Design Thinking en tu vida.');
    closeModalDesignThinking();
}

// Ritual misterioso
function openModalRitual() {
    document.getElementById('modal-ritual').style.display = 'flex';
}
function closeModalRitual() {
    document.getElementById('modal-ritual').style.display = 'none';
}
function confirmPurchaseRitual() {
    alert('Gracias por adquirir Ritual misterioso.');
    closeModalRitual();
}

function openModalConocete() {
    document.getElementById('modal-conocete').style.display = 'flex';
}

function closeModalConocete() {
    document.getElementById('modal-conocete').style.display = 'none';
}

function confirmPurchaseConocete() {
    alert('Gracias por adquirir el servicio Conócete aquí. Recibirás pronto tu cuestionario.');
    closeModalConocete();
}

function acceptDisclaimer() {
    document.getElementById('disclaimer-modal').style.display = 'none';
}

function declineDisclaimer() {
    window.location.href = "https://www.google.com";
}

window.addEventListener('load', function () {
    document.getElementById('disclaimer-modal').style.display = 'flex';
});