var SECUENCE = [];
var RESULT_NUM = -1;
var arx = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36];

function get_roulette_changes() {
  fetch('/get_roulette_changes')
    .then(response => response.json())
    .then(data => {
      show_roulette_free_numbers(data.free_numbers);
      show_roulette_result(data.roulette_result);

    })
    .catch(error => {
      // Manejar cualquier error que ocurra
      console.error(error);
    });
}

function show_roulette_free_numbers(numbers){
  const numeros = numbers.replace('{', '').replace('}', '');
  const my_array = numeros.split(',');

  arx.forEach(function(num) {
    if (num > 0){
      //console.log( my_array, 'roulette_btn_' + num);
      document.getElementById('roulette_btn_' + num).classList.remove('bg-danger');
      document.getElementById('roulette_btn_' + num).classList.remove('bg-success');
      document.getElementById('roulette_btn_' + num).classList.add('bg-secondary');
    }
  });

  my_array.forEach(function(num) {
    if (num >0){
      document.getElementById('roulette_btn_' + num).classList.remove('bg-success');
      document.getElementById('roulette_btn_' + num).classList.remove('bg-secondary');
      document.getElementById('roulette_btn_' + num).classList.add('bg-danger');
    }
  });
}


function show_roulette_result(number){
  if (number > 0){
    arx.forEach(function(num) {
      document.getElementById('roulette_btn_' + num).classList.remove('bg-danger');
      document.getElementById('roulette_btn_' + num).classList.remove('bg-success');
      document.getElementById('roulette_btn_' + num).classList.add('bg-secondary');
      document.getElementById('roulette_btn_' + num).classList.remove('bg-warning');
    });
    document.getElementById('roulette_btn_' + number).classList.add('bg-warning');
  }
}

function set_result_number(number){
  if (SECUENCE.length == 5){
    RESULT_NUM = number;
    Swal.fire({
      title: 'NUMERO GANADOR',
      text: '¡🎰 Seleccionaste el #' + number+'!' + '\nSi es correcto de clic en Reportar (P6)',
      icon: 'info',
      confirmButtonText: 'OK'
    });
  }else{
    Swal.fire({
      title: 'SECUENCIA INCORRECTA',
      text: 'No es momento de indicar esto. Por favor, siga la secuencia 1-2-3...',
      icon: 'warning',
      confirmButtonText: 'OK'
    });
  }
}

function set_crupier_step(step){
  var buttons = document.querySelectorAll("button[name='crp_steps']");
  document.getElementById('crupier_step_' + step).classList.add('btn-danger');
}

function set_open_numbers() {
  if ( JSON.stringify(SECUENCE) == JSON.stringify([]) ) {
    SECUENCE.push(1);
    document.getElementById('crupier_step_1').disabled = true;
    set_crupier_step(1);
    fetch('/set_open_numbers')
      .then(response => response.json())
      .then(data => {
          /*Automaticamente da paso a que hagan apuestas*/
          bet_now();
      }).catch(error => {
        // Manejar cualquier error que ocurra
        console.error(error);
      });
  }else{
    Swal.fire({
      title: 'SECUENCIA INCORRECTA',
      text: 'Siga la secuencia',
      icon: 'error',
      confirmButtonText: 'OK'
    });
  }
}

function bet_now() {
  if (JSON.stringify(SECUENCE) == JSON.stringify([1]) ){
    SECUENCE.push(2);
    document.getElementById('crupier_step_2').disabled = true;
    set_crupier_step(2);
    fetch('/bet_now')
      .then(response => response.json())
      .then(data => {
          //document.getElementById('report_win_btn').disabled = true;
          //document.getElementById('report_loss_btn').disabled = true;
          /*Swal.fire({
            title: 'Recibido',
            text: data.message,
            icon: 'info',
            confirmButtonText: 'OK'
          });*/
      }).catch(error => {
        // Manejar cualquier error que ocurra
        console.error(error);
      });
  }else{
    Swal.fire({
      title: 'SECUENCIA INCORRECTA',
      text: 'Debe seguir la secuencia',
      icon: 'error',
      confirmButtonText: 'OK'
    });
  }
}

function no_more_bets() {
  if ( JSON.stringify(SECUENCE) == JSON.stringify([1, 2]) ){
    SECUENCE.push(3);
    document.getElementById('crupier_step_3').disabled = true;
    set_crupier_step(3);
    fetch('/no_more_bets')
      .then(response => response.json())
      .then(data => {
          //document.getElementById('report_win_btn').disabled = true;
          //document.getElementById('report_loss_btn').disabled = true;
          Swal.fire({
            title: 'NO VA MAS',
            text: data.message + ' Vaya a (P4)',
            icon: 'info',
            confirmButtonText: 'OK'
          });
      }).catch(error => {
        // Manejar cualquier error que ocurra
        console.error(error);
      });
  
  }else{
    Swal.fire({
      title: 'SECUENCIA INCORRECTA',
      text: 'Debe seguir la secuencia',
      icon: 'error',
      confirmButtonText: 'OK'
    });
  }
}

function calculate_unitary_amount(mode){
  if ( JSON.stringify(SECUENCE) == JSON.stringify([1, 2, 3]) ){
    SECUENCE.push(4);
    document.getElementById('crupier_step_4').disabled = true;
    set_crupier_step(4);

    const data = {mode: mode};
    fetch('/calculate_unitary_amount',{
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
      })
      .then(response => response.json())
      .then(data => {
          //document.getElementById('report_win_btn').disabled = true;
          //document.getElementById('report_loss_btn').disabled = true;
          /*Swal.fire({
            title: 'Recibido',
            text: data.message,
            icon: "info",
            confirmButtonText: "OK"
          });*/
          /*Actualizar monto a colocar para que administrador sepa lo que ocurre*/
          document.getElementById('put_coin').innerText = data.total_units;
          spin_roulette();
      }).catch(error => {
        // Manejar cualquier error que ocurra
        console.error(error);
      });
  }else{
    Swal.fire({
      title: 'SECUENCIA INCORRECTA',
      text: 'Debe seguir la secuencia',
      icon: 'error',
      confirmButtonText: 'OK'
    });
  }
}

function spin_roulette(){
  if ( JSON.stringify(SECUENCE) == JSON.stringify([1, 2, 3, 4]) ){
    SECUENCE.push(5);
    document.getElementById('crupier_step_5').disabled = true;
    set_crupier_step(5);
    fetch('/spin_roulette')
      .then(response => response.json())
      .then(data => {
          //document.getElementById('report_win_btn').disabled = true;
          //document.getElementById('report_loss_btn').disabled = true;
          Swal.fire({
            title: 'Completado',
            text: data.message,
            icon: 'warning',
            confirmButtonText: 'OK'
          });
      }).catch(error => {
        // Manejar cualquier error que ocurra
        console.error(error);
      });
  }else{
    Swal.fire({
      title: 'SECUENCIA INCORRECTA',
      text: 'Debe seguir la secuencia',
      icon: 'error',
      confirmButtonText: 'OK'
    });
  }
}

function publish_result(){
  if (RESULT_NUM == -1){
    Swal.fire({
      title: 'MARQUE NUMERO GANADOR',
      text: '🎰 Por favor, marca el número que resultó ganador y vuelve a dar clic aquí',
      icon: 'info',
      confirmButtonText: 'OK'
    });
  }else{
    const data = {roulette_result: RESULT_NUM};
    if ( JSON.stringify(SECUENCE) == JSON.stringify([1, 2, 3, 4, 5]) ){
      SECUENCE.push(6);
      document.getElementById('crupier_step_6').disabled = true;
      set_crupier_step(6);

      fetch('/publish_result', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
      })
        .then(response => response.json())
        .then(data => {
            //document.getElementById('report_win_btn').disabled = false;
            //document.getElementById('report_loss_btn').disabled = false;
            Swal.fire({
              title: 'Completado',
              text: data.message,
              icon: 'info',
              confirmButtonText: 'OK'
            });
        })
        .catch(error => {
          // Manejar cualquier error que ocurra
          console.error(error);
        });
    }else{
      Swal.fire({
        title: 'SECUENCIA INCORRECTA',
        text: 'Debe seguir la secuencia',
        icon: 'error',
        confirmButtonText: 'OK'
      });
    }
  }
}

function reset_all(){
    var buttons = document.querySelectorAll("button[name='crp_steps']");
    if (SECUENCE.length >= 6 || SECUENCE.length < 1){
      fetch('/set_new_round')
        .then(response => response.json())
        .then(data => {
          if (data.status == true){
            /**/
          }else{
            Swal.fire({
              title: 'INFO',
              text: data.message,
              icon: 'error',
              confirmButtonText: 'OK'
            });
          }
        }).catch(error => {
          // Manejar cualquier error que ocurra
          console.error(error);
        });
        /*initial_data();*/
        window.location.replace('/');
    }else{
      Swal.fire({
        title: 'DENEGADO',
        text: 'No puedes hacer una nueva ronda en esta etapa',
        icon: 'error',
        confirmButtonText: 'OK'
      });
    }    
}


function initial_data(){
    fetch('/get_roulette_changes')
      .then(response => response.json())
      .then(data => {
        SECUENCE = [];
        for (let step = 1; step <= data.crupier_step; step++) {
          document.getElementById('crupier_step_' + step).classList.remove('btn-secondary');
          document.getElementById('crupier_step_' + step).classList.add('btn-danger');
          document.getElementById('crupier_step_' + step).disabled = true;
          if (SECUENCE.length < 6){
            SECUENCE.push(step);
          }
        }
      }).catch(error => {
        // Manejar cualquier error que ocurra
        console.error(error);
      });
}

initial_data();

// Ejecutar la función cada 1 segundo
var int_up = setInterval(get_roulette_changes, 2000);