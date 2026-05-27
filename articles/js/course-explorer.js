(function() {

  // Load the data
  d3.json("/articles/data/course-explorer.json").then(initExplorer);

  function initExplorer(courses) {
    // Set up search
    const searchInput = document.getElementById("course-search");
    const suggestionsDiv = document.getElementById("course-suggestions");
    
    // Default: show Augusta first
    let selectedCourse = courses.find(c => c.name === "Augusta National Golf Club") || courses[0];
    renderCourse(selectedCourse);
    
    // Search filter
    searchInput.addEventListener("input", (e) => {
      const query = e.target.value.toLowerCase();
      if (!query) {
        suggestionsDiv.innerHTML = "";
        return;
      }
      
      const matches = courses
        .filter(c => c.name.toLowerCase().includes(query))
        .slice(0, 8);
      
      suggestionsDiv.innerHTML = matches.map(c => 
        `<div class="suggestion" data-name="${c.name}">${c.name}</div>`
      ).join("");
      
      suggestionsDiv.querySelectorAll(".suggestion").forEach(el => {
        el.addEventListener("click", () => {
          const found = courses.find(c => c.name === el.dataset.name);
          if (found) {
            selectedCourse = found;
            searchInput.value = "";
            suggestionsDiv.innerHTML = "";
            renderCourse(selectedCourse);
          }
        });
      });
    });
  }


  function renderCourse(course) {
    // Show course meta
    document.getElementById("selected-course-name").textContent = course.name;
    document.getElementById("course-meta").innerHTML = `
      <span>${course.country || "—"}</span>
      <span>${course.yardage ? course.yardage + " yds" : ""}</span>
      <span>${course.course_type || ""}</span>
      <span>${course.designer ? "Designed by " + course.designer : ""}</span>
      <span>${course.n_events ? course.n_events + " events" : ""}</span>
    `;
    
    // Render radar
    drawRadar(course.percentiles);
  }


  function drawRadar(percentiles) {
    const features = ["sg_app", "sg_arg", "sg_putt", "driving_dist", "driving_acc"];
    const featureLabels = {
      // sg_ott: "SG: Off the Tee",
      sg_app: "SG: Approach",
      sg_arg: "SG: Around Green",
      sg_putt: "SG: Putting",
      driving_dist: "Driving Distance",
      driving_acc: "Driving Accuracy",
      // gir: "Greens in Reg.",
    };
    
    // SVG setup
    const svg = d3.select("#course-radar");
    svg.selectAll("*").remove();  // clear previous
    
    const width = 600;
    const height = 600;
    const center = { x: width / 2, y: height / 2 };
    const radius = 220;
    
    // Brand colors
    const INK = "#363334";
    const PAPER = "#f9f8f3";
    const PURPLE = "#6f5d8e";  // For the highlighted course
    const GRAY = "rgba(54, 51, 52, 0.4)";  // For the baseline
    
    // Compute polygon points
    const numFeatures = features.length;
    const angleSlice = (Math.PI * 2) / numFeatures;
    
    const angle = (i) => i * angleSlice - Math.PI / 2;
    
    // Draw concentric rings (25%, 50%, 75%, 100%)
    [0.25, 0.5, 0.75, 1.0].forEach(level => {
      svg.append("circle")
        .attr("cx", center.x)
        .attr("cy", center.y)
        .attr("r", radius * level)
        .attr("fill", "none")
        .attr("stroke", "rgba(54, 51, 52, 0.15)")
        .attr("stroke-width", 1);
    });
    
    // Draw axis lines
    features.forEach((_, i) => {
      const x2 = center.x + radius * Math.cos(angle(i));
      const y2 = center.y + radius * Math.sin(angle(i));
      svg.append("line")
        .attr("x1", center.x).attr("y1", center.y)
        .attr("x2", x2).attr("y2", y2)
        .attr("stroke", "rgba(54, 51, 52, 0.15)")
        .attr("stroke-width", 1);
    });
    
    // Draw feature labels
    features.forEach((feat, i) => {
      const labelOffset = 30;
      const x = center.x + (radius + labelOffset) * Math.cos(angle(i));
      const y = center.y + (radius + labelOffset) * Math.sin(angle(i));
      svg.append("text")
        .attr("x", x).attr("y", y)
        .attr("text-anchor", "middle")
        .attr("dominant-baseline", "central")
        .attr("font-family", "Archivo, sans-serif")
        .attr("font-size", 11)
        .attr("font-weight", 600)
        .attr("fill", INK)
        .text(featureLabels[feat]);
    });
    
    // Baseline (50% on every axis)
    const baselinePoints = features.map((_, i) => {
      const r = radius * 0.5;
      return [
        center.x + r * Math.cos(angle(i)),
        center.y + r * Math.sin(angle(i)),
      ];
    });
    
    svg.append("polygon")
      .attr("points", baselinePoints.map(p => p.join(",")).join(" "))
      .attr("fill", GRAY)
      .attr("fill-opacity", 0.15)
      .attr("stroke", GRAY)
      .attr("stroke-width", 1);
    
    // Course polygon
    const coursePoints = features.map((feat, i) => {
      const pct = percentiles[feat] || 50;
      const r = (radius * pct) / 100;
      return [
        center.x + r * Math.cos(angle(i)),
        center.y + r * Math.sin(angle(i)),
      ];
    });
    
    svg.append("polygon")
      .attr("points", coursePoints.map(p => p.join(",")).join(" "))
      .attr("fill", PURPLE)
      .attr("fill-opacity", 0.25)
      .attr("stroke", PURPLE)
      .attr("stroke-width", 2.5);
    
    // Dots on each vertex
    features.forEach((feat, i) => {
      const pct = percentiles[feat] || 50;
      const r = (radius * pct) / 100;
      const x = center.x + r * Math.cos(angle(i));
      const y = center.y + r * Math.sin(angle(i));
      
      svg.append("circle")
        .attr("cx", x).attr("cy", y)
        .attr("r", 4)
        .attr("fill", PURPLE)
        .attr("stroke", INK)
        .attr("stroke-width", 1);
    });
  }
})();