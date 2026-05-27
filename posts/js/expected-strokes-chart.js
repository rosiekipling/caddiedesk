(function() {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", init);
    } else {
      init();
    }
  
  
    function init() {
      const container = document.getElementById("expected-strokes-chart");
      if (!container) return;
  
      d3.json("/posts/data/expected-strokes.json").then(drawChart);
    }
  
  
    function drawChart(data) {
      const INK = "#363334";
      const PAPER = "#f9f8f3";
      const lieColors = {
        fairway: "#a3a380",
        rough: "#c1666b",
        sand: "#d4a373",
      };
  
      const svg = d3.select("#expected-strokes-chart");
      svg.selectAll("*").remove();
  
      const width = 800;
      const height = 480;
      const margin = { top: 40, right: 80, bottom: 70, left: 70 };
      const innerWidth = width - margin.left - margin.right;
      const innerHeight = height - margin.top - margin.bottom;
  
      svg.attr("viewBox", `0 0 ${width} ${height}`);
  
      const g = svg.append("g")
        .attr("transform", `translate(${margin.left},${margin.top})`);
  
      // Combine all values to determine scale ranges
      const allPoints = [...data.fairway, ...data.rough, ...data.sand];
  
      const x = d3.scaleLinear()
        .domain([0, d3.max(allPoints, d => d.distance)])
        .nice()
        .range([0, innerWidth]);
  
      const y = d3.scaleLinear()
        .domain([1.5, d3.max(allPoints, d => d.expected_strokes) + 0.2])
        .nice()
        .range([innerHeight, 0]);
  
      // Grid lines
      g.append("g")
        .attr("class", "es-grid")
        .selectAll("line.y-grid")
        .data(y.ticks(6))
        .join("line")
        .attr("class", "y-grid")
        .attr("x1", 0).attr("x2", innerWidth)
        .attr("y1", d => y(d)).attr("y2", d => y(d))
        .attr("stroke", INK)
        .attr("stroke-opacity", 0.08)
        .attr("stroke-dasharray", "3 3");
  
      // Axes
      g.append("g")
        .attr("class", "chart-axis")
        .attr("transform", `translate(0,${innerHeight})`)
        .call(d3.axisBottom(x).ticks(8).tickFormat(d => `${d} yds`));
  
      g.append("g")
        .attr("class", "chart-axis")
        .call(d3.axisLeft(y).ticks(6));
  
      // Axis labels
      g.append("text")
        .attr("x", innerWidth / 2)
        .attr("y", innerHeight + 50)
        .attr("text-anchor", "middle")
        .attr("font-family", "Fraunces, serif")
        .attr("font-size", 13)
        .attr("font-style", "italic")
        .attr("fill", INK)
        .text("Distance to hole");
  
      g.append("text")
        .attr("transform", `translate(-45,${innerHeight / 2}) rotate(-90)`)
        .attr("text-anchor", "middle")
        .attr("font-family", "Fraunces, serif")
        .attr("font-size", 13)
        .attr("font-style", "italic")
        .attr("fill", INK)
        .text("Expected strokes to hole out");
  
      // Line generator
      const line = d3.line()
        .x(d => x(d.distance))
        .y(d => y(d.expected_strokes))
        .curve(d3.curveMonotoneX);
  
      // Draw each lie type
      const lieTypes = ["fairway", "rough", "sand"];
  
      lieTypes.forEach(lie => {
        g.append("path")
          .datum(data[lie])
          .attr("class", `es-line es-line-${lie}`)
          .attr("fill", "none")
          .attr("stroke", lieColors[lie])
          .attr("stroke-width", 3)
          .attr("d", line);
  
        // End-of-line label
        const lastPoint = data[lie][data[lie].length - 1];
        g.append("text")
          .attr("x", x(lastPoint.distance) + 8)
          .attr("y", y(lastPoint.expected_strokes) + 4)
          .attr("font-family", "Archivo, sans-serif")
          .attr("font-size", 11)
          .attr("font-weight", 700)
          .attr("letter-spacing", "0.1em")
          .attr("fill", lieColors[lie])
          .text(lie.toUpperCase());
      });
  
      // Annotations
      data.annotations.forEach(annot => {
        const cx = x(annot.distance);
        const cy = y(annot.expected_strokes);
  
        g.append("circle")
          .attr("cx", cx).attr("cy", cy)
          .attr("r", 6)
          .attr("fill", INK)
          .attr("stroke", PAPER)
          .attr("stroke-width", 2);
  
        g.append("line")
          .attr("x1", cx + 10).attr("y1", cy )
          .attr("x2", cx + 58).attr("y2", cy )
          .attr("stroke", INK)
          .attr("stroke-width", 1);
  
        g.append("text")
          .attr("x", cx + 65)
          .attr("y", cy - 5)
          .attr("font-family", "Fraunces, serif")
          .attr("font-style", "italic")
          .attr("font-size", 13)
          .attr("fill", INK)
          .text(annot.label);
  
        g.append("text")
          .attr("x", cx + 65)
          .attr("y", cy + 15)
          .attr("font-family", "Fraunces, serif")
          .attr("font-weight", 700)
          .attr("font-size", 16)
          .attr("fill", INK)
          .text(`${annot.expected_strokes} expected strokes`);
      });
  
      // Hover overlay
      const tooltip = d3.select(svg.node().parentNode)
        .append("div")
        .attr("class", "es-tooltip");
  
      const focus = g.append("g")
        .style("display", "none");
  
      focus.append("line")
        .attr("class", "es-focus-line")
        .attr("y1", 0)
        .attr("y2", innerHeight)
        .attr("stroke", INK)
        .attr("stroke-opacity", 0.3)
        .attr("stroke-dasharray", "3 3");
  
      const overlay = g.append("rect")
        .attr("width", innerWidth)
        .attr("height", innerHeight)
        .attr("fill", "transparent")
        .style("cursor", "crosshair");
  
      overlay
        .on("mouseover", () => {
          focus.style("display", null);
          tooltip.style("opacity", 1);
        })
        .on("mouseout", () => {
          focus.style("display", "none");
          tooltip.style("opacity", 0);
        })
        .on("mousemove", function(event) {
          const [mouseX] = d3.pointer(event);
          const dist = x.invert(mouseX);
  
          focus.select(".es-focus-line").attr("x1", mouseX).attr("x2", mouseX);
  
          // Find nearest values from each curve
          const lookup = lieTypes.map(lie => {
            const arr = data[lie];
            if (dist < arr[0].distance || dist > arr[arr.length - 1].distance) {
              return null;
            }
            // Linear interpolation
            for (let i = 0; i < arr.length - 1; i++) {
              if (arr[i].distance <= dist && dist <= arr[i + 1].distance) {
                const t = (dist - arr[i].distance) / (arr[i + 1].distance - arr[i].distance);
                const value = arr[i].expected_strokes + t * (arr[i + 1].expected_strokes - arr[i].expected_strokes);
                return { lie, value };
              }
            }
            return null;
          }).filter(Boolean);
  
          const rect = svg.node().parentNode.getBoundingClientRect();
          tooltip
            .style("left", (event.clientX - rect.left + 12) + "px")
            .style("top", (event.clientY - rect.top + 12) + "px")
            .html(`
              <div class="es-tooltip-dist">${Math.round(dist)} yards</div>
              ${lookup.map(l => `
                <div class="es-tooltip-row">
                  <span class="es-tooltip-lie" style="color: ${lieColors[l.lie]}">${l.lie}</span>
                  <span class="es-tooltip-value">${l.value.toFixed(2)}</span>
                </div>
              `).join("")}
            `);
        });

        // Plot Broadie's actual data points as dots over the smooth curves
    const anchors = data.anchors;
    Object.entries(anchors).forEach(([lie, points]) => {
      if (!lieColors[lie]) return;
      g.selectAll(`.es-anchor-${lie}`)
        .data(points)
        .join("circle")
        .attr("class", `es-anchor-${lie}`)
        .attr("cx", d => x(d.distance))
        .attr("cy", d => y(d.expected_strokes))
        .attr("r", 3.5)
        .attr("fill", "#f9f8f3")
        .attr("stroke", lieColors[lie])
        .attr("stroke-width", 2)
        .style("pointer-events", "none");
    });
    }
  })();