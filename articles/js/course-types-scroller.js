(function() {

  d3.json("/articles/data/course-types.json").then(initScrollers);

  let allData = {};

  const features = [ "sg_app", "sg_arg", "sg_putt", "driving_dist", "driving_acc"];
  const featureLabels = {
    sg_app: "SG: Approach",
    sg_arg: "SG: Around Green",
    sg_putt: "SG: Putting",
    driving_dist: "Driving Distance",
    driving_acc: "Driving Accuracy",
  };

  const typeColors = {
    parkland: "#a3a380",
    links: "#3a7d44",
    coastal: "#5a8ca8",
    stadium: "#c1666b",
    // Parkland eras
    golden_age: "#8b6f47",
    modern: "#5a8ca8",
    contemporary: "#3a7d44",
    // Outliers
    augusta: "#5b3924",
    kapalua: "#d4a373",
    standrews: "#6f5d8e",
  };

  const INK = "#363334";
  const radius = 200;
  const center = { x: 300, y: 300 };
  const angleSlice = (Math.PI * 2) / features.length;
  const angle = (i) => i * angleSlice - Math.PI / 2;


  function initScrollers(data) {
    allData = data;
    
    // Scroller 1: Course types
    setupScroller({
      containerId: "scrolly-course-types",
      svgId: "course-type-radar",
      kickerId: "current-kicker",
      nameId: "current-type-name",
      countId: "current-type-count",
      defaultStep: "parkland",
    });
    
    // Scroller 2: Parkland eras
    setupScroller({
      containerId: "scrolly-parkland-eras",
      svgId: "parkland-era-radar",
      kickerId: "era-kicker",
      nameId: "era-name",
      countId: "era-count",
      defaultStep: "golden_age",
    });
    
    // Scroller 3: Outliers (Augusta, Kapalua, St Andrews)
    setupScroller({
      containerId: "scrolly-outliers",
      svgId: "outlier-radar",
      kickerId: "outlier-kicker",
      nameId: "outlier-name",
      countId: "outlier-meta",
      defaultStep: "augusta",
    });
  }


  function setupScroller(config) {
    drawBaseRadar(config.svgId);
    renderStep(config.defaultStep, config);
    
    const isMobile = window.matchMedia("(max-width: 780px)").matches;

    const scroller = scrollama();
    scroller
      .setup({
        step: `#${config.containerId} .scrolly-step`,
        offset: isMobile ? 0.75 : 0.5,
        debug: false,
      })
      .onStepEnter(({ element }) => {
        document.querySelectorAll(`#${config.containerId} .scrolly-step`)
          .forEach(s => s.classList.remove("is-active"));
        element.classList.add("is-active");
        
        const stepKey = element.dataset.step;
        if (stepKey) renderStep(stepKey, config);
      });
  }


  function drawBaseRadar(svgId) {
    const svg = d3.select(`#${svgId}`);
    svg.selectAll("*").remove();
    
    [0.25, 0.5, 0.75, 1.0].forEach(level => {
      svg.append("circle")
        .attr("cx", center.x).attr("cy", center.y)
        .attr("r", radius * level)
        .attr("fill", "none")
        .attr("stroke", "rgba(54, 51, 52, 0.15)");
    });
    
    features.forEach((_, i) => {
      const x = center.x + radius * Math.cos(angle(i));
      const y = center.y + radius * Math.sin(angle(i));
      svg.append("line")
        .attr("x1", center.x).attr("y1", center.y)
        .attr("x2", x).attr("y2", y)
        .attr("stroke", "rgba(54, 51, 52, 0.15)");
    });
    
    features.forEach((feat, i) => {
      const isMobile = window.matchMedia("(max-width: 780px)").matches;
      const labelSize = isMobile ? 20 : 13;
      const labelOffset = isMobile ? 32 : 30;
      
      const x = center.x + (radius + labelOffset) * Math.cos(angle(i));
      const y = center.y + (radius + labelOffset) * Math.sin(angle(i));
      svg.append("text")
        .attr("x", x).attr("y", y)
        .attr("text-anchor", "middle")
        .attr("dominant-baseline", "central")
        .attr("font-family", "Archivo, sans-serif")
        .attr("font-size", labelSize)
        .attr("font-weight", 600)
        .attr("fill", INK)
        .text(featureLabels[feat]);
    });
    
    const baselinePoints = features.map((_, i) => {
      const r = radius * 0.5;
      return [
        center.x + r * Math.cos(angle(i)),
        center.y + r * Math.sin(angle(i)),
      ];
    });
    
    svg.append("polygon")
      .attr("points", baselinePoints.map(p => p.join(",")).join(" "))
      .attr("fill", "rgba(54, 51, 52, 0.08)")
      .attr("stroke", "rgba(54, 51, 52, 0.4)")
      .attr("stroke-width", 1);
    
    svg.append("polygon").attr("class", "active-polygon").attr("id", `${svgId}-active`);
  }


  function renderStep(stepKey, config) {
    const stepData = allData[stepKey];
    if (!stepData) return;
    
    const captionKicker = document.getElementById(config.kickerId);
    const captionH3 = document.getElementById(config.nameId);
    const captionP = document.getElementById(config.countId);
    
    if (stepData.type === "course") {
      captionKicker.textContent = "Outlier";
      captionH3.textContent = stepData.display_name;
      let metaText = [];
      if (stepData.yardage) metaText.push(`${stepData.yardage} yds`);
      if (stepData.country) metaText.push(stepData.country);
      if (stepData.n_events) metaText.push(`${stepData.n_events} events`);
      captionP.textContent = metaText.join(" · ");
    } else if (stepData.type === "parkland_era") {
      captionKicker.textContent = "Parkland Era";
      captionH3.textContent = stepData.display_name;
      captionP.textContent = `${stepData.n_courses} courses`;
    } else {
      captionKicker.textContent = "Course Type";
      captionH3.textContent = stepKey.charAt(0).toUpperCase() + stepKey.slice(1);
      captionP.textContent = `${stepData.n_courses} courses`;
    }
    
    const newPoints = features.map((feat, i) => {
      const pct = stepData.percentiles[feat] || 50;
      const r = (radius * pct) / 100;
      return [
        center.x + r * Math.cos(angle(i)),
        center.y + r * Math.sin(angle(i)),
      ];
    });
    
    const color = typeColors[stepKey] || INK;
    
    d3.select(`#${config.svgId}-active`)
      .transition()
      .duration(500)
      .ease(d3.easeBackOut.overshoot(1.4))
      .attr("points", newPoints.map(p => p.join(",")).join(" "))
      .attr("fill", `${color}40`)
      .attr("stroke", color)
      .attr("stroke-width", 2.5);
  }

})();

(function() {
  const scrollySections = document.querySelectorAll('.scrolly');
  if (!scrollySections.length) return;
  
  const activeSet = new Set();
  
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        activeSet.add(entry.target);
      } else {
        activeSet.delete(entry.target);
      }
    });
    document.body.classList.toggle('scrolly-active', activeSet.size > 0);
  }, {
    rootMargin: '0px 0px -80% 0px',  // activates when section enters top 20% of viewport
    threshold: 0,
  });
  
  scrollySections.forEach(s => observer.observe(s));
})();