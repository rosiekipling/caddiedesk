// posts/js/expected-strokes-putting-chart.js
(function() {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", init);
    } else {
      init();
    }
  
  
    function init() {
      const container = document.getElementById("expected-strokes-putting-chart");
      if (!container) return;
  
      d3.json("/articles/data/expected-strokes.json").then(drawChart);
    }
  
  
    function drawChart(data) {
      const INK = "#363334";
      const PAPER = "#f9f8f3";
      const PUTTING_COLOR = "#5a8ca8";
  
      const svg = d3.select("#expected-strokes-putting-chart");
      svg.selectAll("*").remove();
  
      const width = 800;
      const height = 420;
      const margin = { top: 40, right: 80, bottom: 70, left: 70 };
      const innerWidth = width - margin.left - margin.right;
      const innerHeight = height - margin.top - margin.bottom;
  
      svg.attr("viewBox", `0 0 ${width} ${height}`);
  
      const g = svg.append("g")
        .attr("transform", `translate(${margin.left},${margin.top})`);
  
      const puttingCurve = data.putting;
      const puttingAnchors = data.anchors.putting;
  
      const x = d3.scaleLinear()
        .domain([0, d3.max(puttingCurve, d => d.distance)])
        .nice()
        .range([0, innerWidth]);
  
      const y = d3.scaleLinear()
        .domain([1.0, d3.max(puttingCurve, d => d.expected_strokes) + 0.1])
        .nice()
        .range([innerHeight, 0]);
  
      // Grid lines
      g.append("g")
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
        .call(d3.axisBottom(x).ticks(8).tickFormat(d => `${d} ft`));
  
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
        .text("Distance to hole")
        .style("pointer-events", "none");
  
      g.append("text")
        .attr("transform", `translate(-45,${innerHeight / 2}) rotate(-90)`)
        .attr("text-anchor", "middle")
        .attr("font-family", "Fraunces, serif")
        .attr("font-size", 13)
        .attr("font-style", "italic")
        .attr("fill", INK)
        .text("Expected putts to hole out")
        .style("pointer-events", "none");
  
      // Line generator
      const line = d3.line()
        .x(d => x(d.distance))
        .y(d => y(d.expected_strokes))
        .curve(d3.curveMonotoneX);
  
      // Draw the curve
      g.append("path")
        .datum(puttingCurve)
        .attr("fill", "none")
        .attr("stroke", PUTTING_COLOR)
        .attr("stroke-width", 3)
        .attr("d", line)
        .style("pointer-events", "none");
  
      // End-of-line label
      const lastPoint = puttingCurve[puttingCurve.length - 1];
      g.append("text")
        .attr("x", x(lastPoint.distance) + 8)
        .attr("y", y(lastPoint.expected_strokes) + 4)
        .attr("font-family", "Archivo, sans-serif")
        .attr("font-size", 11)
        .attr("font-weight", 700)
        .attr("letter-spacing", "0.1em")
        .attr("fill", PUTTING_COLOR)
        .text("PUTTING")
        .style("pointer-events", "none");
  
      // Anchor points
      g.selectAll(".es-anchor-putting")
        .data(puttingAnchors)
        .join("circle")
        .attr("class", "es-anchor-putting")
        .attr("cx", d => x(d.distance))
        .attr("cy", d => y(d.expected_strokes))
        .attr("r", 3.5)
        .attr("fill", PAPER)
        .attr("stroke", PUTTING_COLOR)
        .attr("stroke-width", 2)
        .style("pointer-events", "none");
  
      // Annotation: 10 ft putt
      const annot = { distance: 10, expected_strokes: 1.61, label: "10 ft putt" };
      const cx = x(annot.distance);
      const cy = y(annot.expected_strokes);
  
      g.append("circle")
        .attr("cx", cx).attr("cy", cy)
        .attr("r", 6)
        .attr("fill", INK)
        .attr("stroke", PAPER)
        .attr("stroke-width", 2)
        .style("pointer-events", "none");
  
      g.append("line")
        .attr("x1", cx + 8).attr("y1", cy - 4)
        .attr("x2", cx + 60).attr("y2", cy - 35)
        .attr("stroke", INK)
        .attr("stroke-width", 1)
        .style("pointer-events", "none");
  
      g.append("text")
        .attr("x", cx + 65)
        .attr("y", cy - 38)
        .attr("font-family", "Fraunces, serif")
        .attr("font-style", "italic")
        .attr("font-size", 13)
        .attr("fill", INK)
        .text(annot.label)
        .style("pointer-events", "none");
  
      g.append("text")
        .attr("x", cx + 65)
        .attr("y", cy - 22)
        .attr("font-family", "Fraunces, serif")
        .attr("font-weight", 700)
        .attr("font-size", 16)
        .attr("fill", INK)
        .text(`${annot.expected_strokes} expected putts`)
        .style("pointer-events", "none");
  
      // Hover overlay
      // --- Hover overlay ---
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

        if (dist < puttingCurve[0].distance || dist > puttingCurve[puttingCurve.length - 1].distance) {
            tooltip.style("opacity", 0);
            return;
        }

        let value = null;
        for (let i = 0; i < puttingCurve.length - 1; i++) {
            if (puttingCurve[i].distance <= dist && dist <= puttingCurve[i + 1].distance) {
            const t = (dist - puttingCurve[i].distance) / (puttingCurve[i + 1].distance - puttingCurve[i].distance);
            value = puttingCurve[i].expected_strokes + t * (puttingCurve[i + 1].expected_strokes - puttingCurve[i].expected_strokes);
            break;
            }
        }

        if (value === null) return;

        const rect = svg.node().parentNode.getBoundingClientRect();
        tooltip
            .style("opacity", 1)
            .style("left", (event.clientX - rect.left + 12) + "px")
            .style("top", (event.clientY - rect.top + 12) + "px")
            .html(`
            <div class="es-tooltip-dist">${Math.round(dist)} ft</div>
            <div class="es-tooltip-row">
                <span class="es-tooltip-lie" style="color: ${PUTTING_COLOR}">putting</span>
                <span class="es-tooltip-value">${value.toFixed(2)}</span>
            </div>
            `);
        });
    }
  })();