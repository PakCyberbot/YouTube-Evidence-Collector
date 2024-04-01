var menuIcon = document.querySelector(".menu-icon");
var container= document.querySelector(".container");

// Dark Light Mode
let darkModeIcon = document.querySelector('#darkMode-icon');
// let moonIcon = darkModeIcon.querySelector('i');
let logo = document.querySelector('.logo')

darkModeIcon.onclick = () => {
    darkModeIcon.classList.toggle('bx-sun');
    document.body.classList.toggle('dark-mode');

    if(window.location.href.includes('pages')){
        if (logo.src.endsWith('images/logo-light.png')){
            logo.src = '../images/logo-dark.png';
        }
        else if (logo.src.endsWith('images/logo-dark.png')){
            logo.src = '../images/logo-light.png';
        }
        console.log(logo.src)
    }
    else{
        if (logo.src.endsWith('images/logo-light.png')){
            logo.src = 'images/logo-dark.png';
        }
        else if (logo.src.endsWith('images/logo-dark.png')){
            logo.src = 'images/logo-light.png';
        }
    }
};