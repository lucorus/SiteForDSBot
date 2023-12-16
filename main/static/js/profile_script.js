function togglePopup() {
    var popup = document.getElementById('popup-container');
    var overlay = document.getElementById('overlay');
    popup.style.display = (popup.style.display === 'block') ? 'none' : 'block';
    overlay.style.display = (overlay.style.display === 'block') ? 'none' : 'block';
  }


function confirmAction(isConfirmed) {
    togglePopup();
    if (isConfirmed) {
      // Ваш код для выполнения действия при подтверждении
    } else {
      // Ваш код для выполнения действия при отказе
    }
  }
