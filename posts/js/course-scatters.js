(function() {
  d3.json("/posts/data/course-scatters.json").then(initScrollyScatters);

  const INK = "#363334";
  const yardageColors = ["#f4e4c1", "#c19a6b", "#5b3924"];

  const highlightGroups = {
    coastal: (d) => d.course_type === "coastal",
    links: (d) => d.course_type === "links",
    parkland: (d) => d.course_type === "parkland",
    stadium: (d) => d.course_type === "stadium",
    kapalua: (d) => d.name === "Plantation Course at Kapalua",
    augusta: (d) => d.name === "Augusta National Golf Club",
    legolfnational: (d) => d.name === "Le Golf National",
    standrews: (d) => d.name === "Old Course at St Andrews",
  };

  // Per-scatter chart config (stored so step handlers can re-annotate)
  const scatterConfigs = {};


  function initScrollyScatters(data) {
    const validData = data.filter(d => 
      d.shap && d.yardage && d.shap.driving_dist != null
    );

    scatterConfigs["scatter-driving"] = {
      data: validData,
      xKey: "driving_dist",
      yKey: "driving_acc",
      xLabel: "Driving distance importance →",
      yLabel: "Driving accuracy importance →",
      type: "shap",
    };

    scatterConfigs["scatter-approach"] = {
      data: validData,
      xKey: "sg_app",
      yKey: "sg_putt",
      xLabel: "SG: Approach importance →",
      yLabel: "SG: Putting importance →",
      type: "shap",
    };

    const wellSampledData = validData.filter(d => (d.n_events || 0) >= 3);
    scatterConfigs["scatter-yardage"] = {
      data: wellSampledData,
      xKey: "yardage",
      yKey: "driving_dist",
      xLabel: "Course yardage →",
      yLabel: "Driving distance importance →",
      type: "yardage",
    };

    // Draw all charts (no annotations on initial draw)
    drawScatter("scatter-driving");
    drawScatter("scatter-approach");
    drawScatter("scatter-yardage");

    // Setup scrollers
    setupScroller("scrolly-scatter-driving");
    setupScroller("scrolly-scatter-approach");
    setupScroller("scrolly-scatter-yardage");
  }


  function setupScroller(containerId) {
    const scroller = scrollama();
    scroller
      .setup({
        step: `#${containerId} .scrolly-step`,
        offset: 0.5,
      })
      .onStepEnter(({ element }) => {
        document.querySelectorAll(`#${containerId} .scrolly-step`)
          .forEach(s => s.classList.remove("is-active"));
        element.classList.add("is-active");

        // Apply highlight
        const highlightKey = element.dataset.highlight;
        applyHighlight(containerId, highlightKey);

        // Apply annotations
        const annotateList = element.dataset.annotate || "";
        const annotations = annotateList.split(",").map(s => s.trim()).filter(Boolean);
        applyAnnotations(containerId, annotations);
      });
  }


  function applyHighlight(containerId, highlightKey) {
    const dots = d3.select(`#${containerId}`).selectAll(".scatter-dot");

    if (!highlightKey || highlightKey === "none") {
      dots.classed("dimmed", false).classed("highlighted", false);
      return;
    }

    const filter = highlightGroups[highlightKey];
    if (!filter) return;

    dots.each(function(d) {
      const isMatch = filter(d);
      d3.select(this)
        .classed("highlighted", isMatch)
        .classed("dimmed", !isMatch);
    });
  }


  function applyAnnotations(containerId, courseNames) {
    // Find the right SVG ID based on container
    const containerToSvg = {
      "scrolly-scatter-driving": "scatter-driving",
      "scrolly-scatter-approach": "scatter-approach",
      "scrolly-scatter-yardage": "scatter-yardage",
    };
    const svgId = containerToSvg[containerId];
    if (!svgId) return;

    const config = scatterConfigs[svgId];
    if (!config) return;

    drawAnnotations(svgId, config, courseNames);
  }


  function drawAnnotations(svgId, config, courseNames) {
    const svg = d3.select(`#${svgId}`);
    const g = svg.select("g");

    // Remove old annotations layer, build a new one
    g.select(".annotations-layer").remove();
    const annotLayer = g.append("g").attr("class", "annotations-layer");

    const width = 800;
    const height = 600;
    const margin = { top: 40, right: 60, bottom: 80, left: 80 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    // Reconstruct scales (same as drawScatter)
    const data = config.data;
    let xValues, yValues;
    if (config.type === "yardage") {
      xValues = data.map(d => d.yardage);
      yValues = data.map(d => d.shap.driving_dist);
    } else {
      xValues = data.map(d => d.shap[config.xKey]);
      yValues = data.map(d => d.shap[config.yKey]);
    }

    const x = d3.scaleLinear().domain(d3.extent(xValues)).nice().range([0, innerWidth]);
    const y = d3.scaleLinear().domain(d3.extent(yValues)).nice().range([innerHeight, 0]);

    const getX = config.type === "yardage" 
      ? d => x(d.yardage) 
      : d => x(d.shap[config.xKey]);
    const getY = config.type === "yardage" 
      ? d => y(d.shap.driving_dist) 
      : d => y(d.shap[config.yKey]);

    courseNames.forEach(courseName => {
      const course = data.find(d => d.name === courseName);
      if (!course) return;

      const shortName = courseName
        .replace("Old Course at ", "")
        .replace(" Golf Club", "")
        .replace(" Golf Links", "")
        .replace(" Country Club", "");

      const cx = getX(course);
      const cy = getY(course);
      const offsetX = 20;
      const offsetY = -18;

      const annot = annotLayer.append("g")
        .attr("class", "scatter-annotation-group")
        .style("opacity", 0);

      annot.append("line")
        .attr("class", "scatter-annotation-line")
        .attr("x1", cx + 6).attr("y1", cy - 4)
        .attr("x2", cx + offsetX - 2).attr("y2", cy + offsetY + 4);

      annot.append("text")
        .attr("class", "scatter-annotation")
        .attr("x", cx + offsetX).attr("y", cy + offsetY)
        .text(shortName);

      // Fade in
      annot.transition()
        .duration(400)
        .style("opacity", 1);
    });
  }


  function drawScatter(svgId) {
    const config = scatterConfigs[svgId];
    if (!config) return;

    const svg = d3.select(`#${svgId}`);
    svg.selectAll("*").remove();

    const width = 800;
    const height = 600;
    const margin = { top: 40, right: 60, bottom: 80, left: 80 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const g = svg.append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    const data = config.data;
    let xValues, yValues;
    if (config.type === "yardage") {
      xValues = data.map(d => d.yardage);
      yValues = data.map(d => d.shap.driving_dist);
    } else {
      xValues = data.map(d => d.shap[config.xKey]);
      yValues = data.map(d => d.shap[config.yKey]);
    }

    const x = d3.scaleLinear().domain(d3.extent(xValues)).nice().range([0, innerWidth]);
    const y = d3.scaleLinear().domain(d3.extent(yValues)).nice().range([innerHeight, 0]);

    // Color
    let colorFn;
    if (config.type === "yardage") {
      const typeColors = {
        parkland: "#a3a380", links: "#3a7d44", coastal: "#5a8ca8",
        stadium: "#c1666b", desert: "#d4a373", mountain: "#6f5d8e",
      };
      colorFn = d => typeColors[d.course_type] || "#888";
    } else {
      const yardages = data.map(d => d.yardage);
      const colorScale = d3.scaleLinear()
        .domain([d3.min(yardages), d3.median(yardages), d3.max(yardages)])
        .range(yardageColors);
      colorFn = d => colorScale(d.yardage);
    }

    // Axes
    g.append("g")
      .attr("class", "chart-axis")
      .attr("transform", `translate(0,${innerHeight})`)
      .call(d3.axisBottom(x).ticks(6).tickFormat(d => 
        config.type === "yardage" ? d : d3.format(".2f")(d)
      ));
    g.append("g")
      .attr("class", "chart-axis")
      .call(d3.axisLeft(y).ticks(6).tickFormat(d3.format(".2f")));

    g.append("text")
      .attr("x", innerWidth / 2).attr("y", innerHeight + 50)
      .attr("text-anchor", "middle")
      .attr("font-family", "Fraunces, serif").attr("font-size", 14).attr("fill", INK)
      .text(config.xLabel);

    g.append("text")
      .attr("transform", `translate(-50,${innerHeight / 2}) rotate(-90)`)
      .attr("text-anchor", "middle")
      .attr("font-family", "Fraunces, serif").attr("font-size", 14).attr("fill", INK)
      .text(config.yLabel);

    // Quadrant lines (skip for yardage chart)
    if (config.type !== "yardage") {
      const xMed = d3.median(xValues);
      const yMed = d3.median(yValues);
      g.append("line").attr("class", "scatter-quadrant")
        .attr("x1", x(xMed)).attr("x2", x(xMed)).attr("y1", 0).attr("y2", innerHeight);
      g.append("line").attr("class", "scatter-quadrant")
        .attr("x1", 0).attr("x2", innerWidth).attr("y1", y(yMed)).attr("y2", y(yMed));
    }

    // Regression line for yardage chart
    if (config.type === "yardage") {
      const meanX = d3.mean(xValues);
      const meanY = d3.mean(yValues);
      const num = data.reduce((acc, d) => acc + (d.yardage - meanX) * (d.shap.driving_dist - meanY), 0);
      const denom = data.reduce((acc, d) => acc + Math.pow(d.yardage - meanX, 2), 0);
      const slope = num / denom;
      const intercept = meanY - slope * meanX;
      const sumXX = data.reduce((acc, d) => acc + Math.pow(d.yardage - meanX, 2), 0);
      const sumYY = data.reduce((acc, d) => acc + Math.pow(d.shap.driving_dist - meanY, 2), 0);
      const r = num / Math.sqrt(sumXX * sumYY);

      const xRange = d3.extent(xValues);
      g.append("line")
        .attr("x1", x(xRange[0])).attr("y1", y(slope * xRange[0] + intercept))
        .attr("x2", x(xRange[1])).attr("y2", y(slope * xRange[1] + intercept))
        .attr("stroke", INK).attr("stroke-width", 1.5)
        .attr("stroke-dasharray", "6 4").attr("opacity", 0.5);
      g.append("text")
        .attr("x", innerWidth - 10).attr("y", 0).attr("text-anchor", "end")
        .attr("font-family", "Archivo, sans-serif").attr("font-size", 12)
        .attr("font-weight", 700).attr("fill", INK)
        .text(`r = ${r.toFixed(2)}`);
    }

    // Tooltip
    const tooltip = d3.select(svg.node().parentNode)
      .append("div").attr("class", "scatter-tooltip");

    // Dots
    const getX = config.type === "yardage" 
      ? d => x(d.yardage) 
      : d => x(d.shap[config.xKey]);
    const getY = config.type === "yardage" 
      ? d => y(d.shap.driving_dist) 
      : d => y(d.shap[config.yKey]);

    const dots = g.selectAll(".scatter-dot")
      .data(data).join("circle")
      .attr("class", "scatter-dot")
      .attr("cx", getX).attr("cy", getY)
      .attr("r", 6)
      .attr("fill", colorFn)
      .attr("opacity", 0.7)
      .attr("stroke", INK).attr("stroke-width", 0.5);

    dots
      .on("mouseover", function(event, d) {
        d3.select(this).attr("r", 9).attr("stroke-width", 2);
        tooltip.style("opacity", 1).html(buildTooltip(d, config.xKey, config.yKey, config.type));
      })
      .on("mousemove", function(event) {
        const rect = svg.node().parentNode.getBoundingClientRect();
        tooltip
          .style("left", (event.clientX - rect.left + 12) + "px")
          .style("top", (event.clientY - rect.top + 12) + "px");
      })
      .on("mouseout", function() {
        d3.select(this).attr("r", 6).attr("stroke-width", 0.5);
        tooltip.style("opacity", 0);
      });
  }


  function buildTooltip(d, xKey, yKey, type) {
    const xValue = type === "yardage" ? d.yardage : d.shap[xKey];
    const yValue = type === "yardage" ? d.shap.driving_dist : d.shap[yKey];
    
    return `
      <div class="tooltip-kicker">${d.course_type || ""} ${d.country ? "· " + d.country : ""}</div>
      <div class="tooltip-name">${d.name}</div>
      <div class="tooltip-meta">
        ${d.yardage ? d.yardage + " yds" : ""}
        ${d.designer ? "· " + d.designer : ""}
      </div>
      <div class="tooltip-stats">
        ${d.n_events ? d.n_events + " events" : ""}
      </div>
    `;
  }

})();