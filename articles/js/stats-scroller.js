(function() {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", init);
    } else {
      init();
    }
  
  
    function init() {
      setupIntroScroller();
      setupStatsScroller();
      setupSectionObserver();
    }
  
  
    function setupIntroScroller() {
      if (!document.querySelector(".scrolly-intro-step")) return;
      
      const scroller = scrollama();
      scroller
        .setup({
          step: ".scrolly-intro-step",
          offset: 0.5,
        })
        .onStepEnter(({ element, index }) => {
          // Update step opacity
          document.querySelectorAll(".scrolly-intro-step")
            .forEach((s, i) => {
              s.classList.remove("is-active");
              if (i === index) s.classList.add("is-active");
            });
          
          // Update sidebar progress dots
          document.querySelectorAll(".sidebar-intro .progress-dot")
            .forEach((dot, i) => {
              dot.classList.remove("is-active", "is-past");
              if (i === index) {
                dot.classList.add("is-active");
              } else if (i < index) {
                dot.classList.add("is-past");
              }
            });
        });
    }
  
  
    function setupStatsScroller() {
      if (!document.querySelector(".stats-content .stat-step")) return;
      
      const scroller = scrollama();
      scroller
        .setup({
          step: ".stats-content .stat-step",
          offset: 0.4,
        })
        .onStepEnter(({ element }) => {
          const statKey = element.dataset.step;
          
          // Update sidebar stat highlight
          document.querySelectorAll(".sidebar-stats li")
            .forEach(li => {
              li.classList.remove("is-active");
              if (li.dataset.stat === statKey) {
                li.classList.add("is-active");
              }
            });
        });
      
      // Click-to-jump for accessibility
      document.querySelectorAll(".sidebar-stats li").forEach(li => {
        li.addEventListener("click", () => {
          const statKey = li.dataset.stat;
          const target = document.querySelector(`.stat-step[data-step="${statKey}"]`);
          if (target) {
            target.scrollIntoView({ behavior: "smooth", block: "start" });
          }
        });
      });
    }
  
  
    // Observe which major section is in view — toggle sidebar visibility
    function setupSectionObserver() {
      const intro = document.getElementById("scrolly-intro");
      const stats = document.getElementById("stats-section");
      const sidebarIntro = document.getElementById("sidebar-intro");
      const sidebarStats = document.getElementById("sidebar-stats");
      
      if (!intro || !stats || !sidebarIntro || !sidebarStats) return;
      
      const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.target === intro) {
            sidebarIntro.classList.toggle("is-visible", entry.isIntersecting);
          } else if (entry.target === stats) {
            sidebarStats.classList.toggle("is-visible", entry.isIntersecting);
          }
        });
      }, { rootMargin: "-30% 0px -30% 0px" });
      
      observer.observe(intro);
      observer.observe(stats);
    }
  })();