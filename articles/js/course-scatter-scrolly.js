(function() {
    d3.json("/articles/data/course-scatters.json").then(initScrollyScatter);
    
    const INK = "#363334";
    
    // Groups to highlight per step
    const highlightGroups = {
      coastal: (d) => d.course_type === "coastal",
      links: (d) => d.course_type === "links",
      parkland: (d) => d.course_type === "parkland",
      kapalua: (d) => d.name === "Plantation Course at Kapalua",
      augusta: (d) => d.name === "Augusta National Golf Club",
      // Add more as needed
    };
    
    
    function initScrollyScatter(data) {
      const validData = data.filter(d => 
        d.shap && d.yardage && d.shap.driving_dist != null && d.shap.driving_acc != null
      );
      
      drawScatter({
        svgId: "scatter-driving",
        data: validData,
        xKey: "driving_dist",
        yKey: "driving_acc",
        xLabel: "Driving distance importance →",
        yLabel: "Driving accuracy importance →",
      });
      
      setupScroller("scrolly-scatter-driving");
    }
    
    
    function drawScatter({ svgId, data, xKey, yKey, xLabel, yLabel }) {
      const svg = d3.select(`#${svgId}`);
      svg.selectAll("*").remove();
      
      const width = 800;
      const height = 600;
      const margin = { top: 40, right: 60, bottom: 80, left: 80 };
      const innerWidth = width - margin.left - margin.right;
      const innerHeight = height - margin.top - margin.bottom;
      
      const g = svg.append("g")
        .attr("transform", `translate(${margin.left},${margin.top})`);
      
      const xValues = data.map(d => d.shap[xKey]);
      const yValues = data.map(d => d.shap[yKey]);
      
      const x = d3.scaleLinear()
        .domain(d3.extent(xValues))
        .nice()
        .range([0, innerWidth]);
      
      const y = d3.scaleLinear()
        .domain(d3.extent(yValues))
        .nice()
        .range([innerHeight, 0]);
      
      const typeColors = {
        parkland: "#a3a380",
        links: "#3a7d44",
        coastal: "#5a8ca8",
        stadium: "#c1666b",
        desert: "#d4a373",
        mountain: "#6f5d8e",
      };
      
      // Axes
      g.append("g")
        .attr("class", "chart-axis")
        .attr("transform", `translate(0,${innerHeight})`)
        .call(d3.axisBottom(x).ticks(6).tickFormat(d3.format(".2f")));
      
      g.append("g")
        .attr("class", "chart-axis")
        .call(d3.axisLeft(y).ticks(6).tickFormat(d3.format(".2f")));
      
      g.append("text")
        .attr("x", innerWidth / 2)
        .attr("y", innerHeight + 50)
        .attr("text-anchor", "middle")
        .attr("font-family", "Fraunces, serif")
        .attr("font-size", 14)
        .attr("fill", INK)
        .text(xLabel);
      
      g.append("text")
        .attr("transform", `translate(-50,${innerHeight / 2}) rotate(-90)`)
        .attr("text-anchor", "middle")
        .attr("font-family", "Fraunces, serif")
        .attr("font-size", 14)
        .attr("fill", INK)
        .text(yLabel);
      
      // Quadrant lines
      const xMed = d3.median(xValues);
      const yMed = d3.median(yValues);
      g.append("line")
        .attr("class", "scatter-quadrant")
        .attr("x1", x(xMed)).attr("x2", x(xMed))
        .attr("y1", 0).attr("y2", innerHeight);
      g.append("line")
        .attr("class", "scatter-quadrant")
        .attr("x1", 0).attr("x2", innerWidth)
        .attr("y1", y(yMed)).attr("y2", y(yMed));
      
      // Dots
      g.selectAll(".scatter-dot")
        .data(data)
        .join("circle")
        .attr("class", "scatter-dot")
        .attr("cx", d => x(d.shap[xKey]))
        .attr("cy", d => y(d.shap[yKey]))
        .attr("r", 6)
        .attr("fill", d => typeColors[d.course_type] || "#888")
        .attr("opacity", 0.7)
        .attr("stroke", INK)
        .attr("stroke-width", 0.5);
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
          
          const highlightKey = element.dataset.highlight;
          applyHighlight(highlightKey);
        });
    }
    
    
    function applyHighlight(highlightKey) {
      const dots = d3.selectAll(".scatter-dot");
      
      if (!highlightKey || highlightKey === "none") {
        // Reset to default state
        dots
          .classed("dimmed", false)
          .classed("highlighted", false)
          .transition().duration(400)
          .attr("opacity", 0.7);
        return;
      }
      
      const filter = highlightGroups[highlightKey];
      if (!filter) return;
      
      dots
        .each(function(d) {
          const isMatch = filter(d);
          d3.select(this)
            .classed("highlighted", isMatch)
            .classed("dimmed", !isMatch);
        });
    }
  })();