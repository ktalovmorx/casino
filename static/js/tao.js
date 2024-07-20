
/* Deshabilitar click derecho*/
/*$(document).bind("contextmenu",function(e){
  return false;
    });*/

function open_page(url){
   window.location.replace(url);
}

function set_bet(btn, amount){
  var _switch = document.getElementById('switch');
  const inp = document.getElementById('bet_amount');
  inp.value = amount
  // Obtener una lista de elementos <button> con el atributo name='set_btn'
  var buttons = document.querySelectorAll("button[name='set_btn']");

  // Iterar sobre los elementos y aplicar una nueva clase
  buttons.forEach(function(button) {
    button.classList.remove('btn-success');
    button.classList.add('btn-secondary');
  });
  btn.classList.add('btn-success');
  /*inp.scrollIntoView();*/
  /*inp.focus();*/

  _switch.checked = false;
}

function show_message(title, message, icon){
  Swal.fire({
    title: title,
    text: message,
    icon: icon,
    confirmButtonText: "OK"
  });
}

function exit_table(roulette_id){
  var params = {roulette_id: roulette_id};
  fetch('/exit_table', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(params)
    })
    .then(response => response.json())
    .then(data => {
      window.location.replace(data.url);
    })
    .catch(error => {
    });
}

function put_bet(roulette_id, user_plays, user_covers, roulette_type){
  var _switch = document.getElementById('switch');
  if (_switch.disabled){
      Swal.fire({
        title: 'Espere',
        text: 'Espere que el crupier habilite la colocacion de apuestas',
        icon: "warning",
        confirmButtonText: "OK"
      });
      return false;
  }

  if (roulette_type == 'X2' || roulette_type == 'X3' || roulette_type == 'X6'){
    var bet_amount = null;
  }else{
    var bet_amount = document.getElementById('bet_amount').value;
    if (bet_amount == null || bet_amount == ''){
      Swal.fire({
        title: 'Monto Invalido',
        text: 'Seleccione un monto de la lista de apuestas',
        icon: "error",
        confirmButtonText: "OK"
      });
      _switch.checked = false;
      return false;
    }
  }

  Swal.fire({
    title: 'Confirmar apuesta',
    text: '¿Por favor, indique si desea continuar?',
    icon: 'question',
    showCancelButton: true,
    confirmButtonText: 'Sí',
    cancelButtonText: 'No'
  }).then((result) => {
    if (result.isConfirmed) {

      var params = {bet_amount:bet_amount,
                    roulette_id:roulette_id,
                    if_bet:_switch.checked,
                    user_plays:user_plays,
                    user_covers:user_covers,
                    roulette_type:roulette_type};
      fetch('/put_bet', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(params)
        })
        .then(response => response.json())
        .then(data => {
          Swal.fire({
            title: 'Recibido',
            text: data.info,
            icon: "warning",
            confirmButtonText: "OK"
          });

          if (data.status){
            /*_switch.checked = false;*/
            if (roulette_type == 'X2' || roulette_type == 'X3' || roulette_type == 'X6'){
              /*_switch.checked = true;*/
            }
            if (roulette_type == 'X1'){
              _switch.checked = false;
            }
          }else{
            _switch.checked = false;
          }
          
        })
        .catch(error => {
          // Manejar cualquier error que ocurra
          _switch.checked = false;
        });

    } else if (result.dismiss === Swal.DismissReason.cancel) {
      _switch.checked = false;
      /*alert('Operacion cancelada');*/
          Swal.fire({
            title: 'Atención',
            text: 'Operación cancelada',
            icon: 'warning',
            confirmButtonText: "OK"
          });
    }
  });
}

function toogle_put_bet() {
}