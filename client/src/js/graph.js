// eslint-disable-next-line no-unused-vars
/* global Chart */

let currentChart = null;

/**
 * Renders a price history line chart on the given canvas element.
 * Destroys any existing chart on the same canvas before creating a new one.
 * @param {HTMLCanvasElement} canvasEl - The canvas DOM element to render on.
 * @param {Array<{price: number, timestamp: string}>} prices - Array of price objects.
 */
export function renderPriceChart(canvasEl, prices) {
    if (currentChart) {
        currentChart.destroy();
        currentChart = null;
    }

    const sorted = prices.slice().sort((a, b) => {
        return new Date(a.timestamp) - new Date(b.timestamp);
    });

    const labels = sorted.map(p => {
        const d = new Date(p.timestamp);
        return d.toLocaleDateString() + " " + d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    });
    const data = sorted.map(p => p.price);

    currentChart = new Chart(canvasEl, {
        type: "line",
        data: {
            labels: labels,
            datasets: [{
                label: "Price",
                data: data,
                borderColor: "#4a90d9",
                backgroundColor: "rgba(74, 144, 217, 0.1)",
                fill: true,
                tension: 0.3,
                pointRadius: 3,
                pointHoverRadius: 5,
                borderWidth: 2,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false,
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return "\u20AC" + context.parsed.y.toFixed(2);
                        }
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        maxRotation: 45,
                        minRotation: 45,
                        maxTicksLimit: 10,
                    }
                },
                y: {
                    ticks: {
                        callback: function(value) {
                            return "\u20AC" + value.toFixed(2);
                        }
                    }
                }
            }
        }
    });
}
