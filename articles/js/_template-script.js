// posts/_template-script.js
// Shared scrollytelling behaviour for Caddie Desk articles


window.addEventListener('scroll', () => {
    const scrolled = window.scrollY;
    const max = document.documentElement.scrollHeight - window.innerHeight;
    const pct = (scrolled / max) * 100;
    document.querySelector('.article-progress').style.width = pct + '%';
  });

// Initialise Scrollama for the scrolly sections
function initScrollytelling(onStepEnter, onStepExit) {
    if (typeof scrollama === 'undefined') {
      console.warn('Scrollama not loaded');
      return;
    }
  
    const scroller = scrollama();
    scroller
        .setup({
        step: '.scrolly-step',
        offset: 0.5,
        })
        .onStepEnter(response => {
        // Add active class
        response.element.classList.add('is-active');
        if (onStepEnter) onStepEnter(response);
        })
        .onStepExit(response => {
        response.element.classList.remove('is-active');
        if (onStepExit) onStepExit(response);
        });

    window.addEventListener('resize', scroller.resize);
  
    return scroller;
  }
  
  // Make available to article scripts
  window.initScrollytelling = initScrollytelling;