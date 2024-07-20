var obj_free_nums = document.getElementById('free_numbers');
var obj_tao_nums = document.getElementById('tao_numbers');
var obj_online_users = document.getElementById('online_users');
var obj_rounds_number = document.getElementsByName('round_number');
var _switch = document.getElementById('switch');
var arx = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36];

function set_crupier_step(step){
  var buttons = document.querySelectorAll("button[name='crp_steps']");
  var loaders = document.querySelectorAll("span[name='loader_steps']");

  //Iterar sobre los loaders y ocultarlos todos
  loaders.forEach(function(element) {
    $(element).hide();
  });

  // Iterar sobre los elementos y aplicar una nueva clase
  buttons.forEach(function(element) {
    element.classList.remove('btn-success');
    element.classList.add('btn-secondary');
  });

  /*Solo mostrar los elementos necesarios*/
  if (step > 0 && step < 7){
    document.getElementById('crupier_step_' + step).classList.add('btn-success');
    $('#'+'loader_crupier_step_' + step).show();
  }
}

function show_roulette_free_numbers(numbers){
  const numeros = numbers.replace('{', '').replace('}', '');
  const my_array = numeros.split(',');
  
  arx.forEach(function(num) {
    if (num > 0){
      document.getElementById('roulette_btn_' + num).classList.remove('bg-danger');
      document.getElementById('roulette_btn_' + num).classList.remove('bg-success');
      document.getElementById('roulette_btn_' + num).classList.remove('bg-warning');
      document.getElementById('roulette_btn_' + num).classList.add('bg-secondary');
    }
  });

  my_array.forEach(function(num) {
    if (num > 0){
      document.getElementById('roulette_btn_' + num).classList.remove('bg-success');
      document.getElementById('roulette_btn_' + num).classList.remove('bg-secondary');
      document.getElementById('roulette_btn_' + num).classList.add('bg-danger');
    }
  });
}

function show_roulette_result(number){
  arx.forEach(function(num) {
    if (num > 0){
      document.getElementById('roulette_btn_' + num).classList.remove('bg-danger');
      document.getElementById('roulette_btn_' + num).classList.remove('bg-success');
      document.getElementById('roulette_btn_' + num).classList.add('bg-secondary');
    }
  });
  if (number > 0){
    document.getElementById('roulette_btn_' + number).classList.add('bg-warning');
  }
}

function get_roulette_changes() {
  fetch('/get_roulette_changes')
    .then(response => response.json())
    .then(data => {
      obj_free_nums.innerText = data.free_numbers;
      obj_tao_nums.innerText = data.tao_number;
      obj_online_users.innerText = data.online_users;

      if (data.crupier_step >= 1 && data.crupier_step <= 5){
        show_roulette_free_numbers(data.free_numbers);
      }

      if (data.crupier_step == 6){
        show_roulette_result(data.roulette_result);
      }

      /*Solo habilita el switch de apuesta si vamos en el paso #2*/
      if (data.crupier_step == 2){
        _switch.disabled = false;
      }else{
        _switch.disabled = true;
      }
      set_crupier_step(data.crupier_step);

      for (var i = 0; i < obj_rounds_number.length; i++) {
        var element = obj_rounds_number[i];
        element.innerText = 'Ronda #'+ data.round_number;
      }

      if (data.error){
        clearInterval(int_up);
        window.location.href = '/casino';
      }
      
    })
    .catch(error => {
      // Manejar cualquier error que ocurra
      console.error(error);
    });
}

// Ejecutar la función cada 1 segundo
var int_up = setInterval(get_roulette_changes, 2000);