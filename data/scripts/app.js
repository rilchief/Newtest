(() => {
  const dataset = window.AFROBEATS_DATA;
  if (!dataset || !Array.isArray(dataset.playlists)) {
    console.error("Afrobeats dataset missing or malformed.");
    return;
  }

  const elements = {
    search: document.getElementById("search"),
    curatorTypes: document.getElementById("curator-types"),
    minYear: document.getElementById("min-year"),
    maxYear: document.getElementById("max-year"),
    diasporaOnly: document.getElementById("diaspora-only"),
    reset: document.getElementById("reset-filters"),
    playlistCount: document.getElementById("playlist-count"),
    trackCount: document.getElementById("track-count"),
    nigeriaShare: document.getElementById("nigeria-share"),
    diasporaShare: document.getElementById("diaspora-share"),
    diversityScore: document.getElementById("diversity-score"),
    playlistTable: document.getElementById("playlist-table"),
    emptyState: document.getElementById("empty-state"),
    regionChart: document.getElementById("region-chart"),
    audioChart: document.getElementById("audio-chart"),
    curatorChart: document.getElementById("curator-chart"),
    audioBanner: document.getElementById("audio-status-banner")
  };

  const allTracks = dataset.playlists.flatMap((playlist) => playlist.tracks || []);
  const trackYears = allTracks.map((track) => track.releaseYear).filter((year) => typeof year === "number");
  const minYearValue = Math.min(...trackYears);
  const maxYearValue = Math.max(...trackYears);

  const uniqueCuratorTypes = Array.from(new Set(dataset.playlists.map((p) => p.curatorType))).sort();

  const metadataElements = {
    generated: document.getElementById("data-generated"),
    started: document.getElementById("data-started"),
    playlistTotal: document.getElementById("dataset-playlist-count"),
    missingCount: document.getElementById("dataset-missing-count"),
    audioStatus: document.getElementById("audio-feature-status")
  };

  const state = {
    search: "",
    curatorTypes: new Set(uniqueCuratorTypes),
    minYear: minYearValue,
    maxYear: maxYearValue,
    diasporaOnly: false
  };

  function initFilters() {
    elements.curatorTypes.innerHTML = uniqueCuratorTypes
      .map(
        (type, index) => `
          <label>
            <input type="checkbox" value="${type}" data-index="${index}" checked />
            <span>${type}</span>
          </label>
        `
      )
      .join("");

    elements.minYear.value = state.minYear;
    elements.minYear.min = String(minYearValue);
    elements.minYear.max = String(maxYearValue);

    elements.maxYear.value = state.maxYear;
    elements.maxYear.min = String(minYearValue);
    elements.maxYear.max = String(maxYearValue);
  }

  function attachListeners() {
    elements.search.addEventListener("input", (event) => {
      state.search = event.target.value.trim().toLowerCase();
      updateDashboard();
    });

    elements.curatorTypes.querySelectorAll("input[type=checkbox]").forEach((checkbox) => {
      checkbox.addEventListener("change", (event) => {
        const value = event.target.value;
        if (event.target.checked) {
          state.curatorTypes.add(value);
        } else {
          state.curatorTypes.delete(value);
        }
        if (state.curatorTypes.size === 0) {
          state.curatorTypes.add(value);
          event.target.checked = true;
          return;
        }
        updateDashboard();
      });
    });

    elements.minYear.addEventListener("change", (event) => {
      const value = Number(event.target.value) || minYearValue;
      state.minYear = Math.max(minYearValue, Math.min(value, state.maxYear));
      event.target.value = state.minYear;
      updateDashboard();
    });

    elements.maxYear.addEventListener("change", (event) => {
      const value = Number(event.target.value) || maxYearValue;
      state.maxYear = Math.min(maxYearValue, Math.max(value, state.minYear));
      event.target.value = state.maxYear;
      updateDashboard();
    });

    elements.diasporaOnly.addEventListener("change", (event) => {
      state.diasporaOnly = event.target.checked;
      updateDashboard();
    });

    elements.reset.addEventListener("click", () => {
      state.search = "";
      state.curatorTypes = new Set(uniqueCuratorTypes);
      state.minYear = minYearValue;
      state.maxYear = maxYearValue;
      state.diasporaOnly = false;

      elements.search.value = "";
      elements.minYear.value = minYearValue;
      elements.maxYear.value = maxYearValue;
      elements.diasporaOnly.checked = false;
      elements.curatorTypes.querySelectorAll("input[type=checkbox]").forEach((checkbox) => {
        checkbox.checked = true;
      });

      updateDashboard();
    });
  }

  function filterTracks(playlist) {
    const tracks = playlist.tracks || [];
    return tracks.filter((track) => {
      if (!track) return false;
      if (typeof track.releaseYear !== "number") return false;
      if (track.releaseYear < state.minYear || track.releaseYear > state.maxYear) return false;
      if (state.diasporaOnly && !track.diaspora) return false;
      return true;
    });
  }

  function filterPlaylists() {
    return dataset.playlists
      .filter((playlist) => state.curatorTypes.has(playlist.curatorType))
      .filter((playlist) => playlist.name.toLowerCase().includes(state.search))
      .map((playlist) => ({
        ...playlist,
        filteredTracks: filterTracks(playlist)
      }))
      .filter((playlist) => playlist.filteredTracks.length > 0);
  }

  function average(numbers) {
    if (!numbers.length) return 0;
    const total = numbers.reduce((sum, value) => sum + value, 0);
    return total / numbers.length;
  }

  function sumCounts(tracks, accessor) {
    return tracks.reduce((acc, track) => {
      const key = accessor(track) || "Unknown";
      acc[key] = (acc[key] || 0) + 1;
      return acc;
    }, {});
  }

  function formatNumber(value) {
    if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
    if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
    return String(value);
  }

  function formatPercent(part, total) {
    if (!total) return "0%";
    return `${Math.round((part / total) * 100)}%`;
  }

  function formatTimestamp(value) {
    if (!value) return "Unknown";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
  }

  let charts = {
    region: null,
    audio: null,
    curator: null
  };

  function initMetadata() {
    const runMetadata = dataset.runMetadata || {};
    if (metadataElements.generated) {
      metadataElements.generated.textContent = formatTimestamp(runMetadata.generatedAt);
    }
    if (metadataElements.started) {
      metadataElements.started.textContent = formatTimestamp(runMetadata.startedAt);
    }
    if (metadataElements.playlistTotal) {
      const runCount = typeof runMetadata.playlistCount === "number" ? runMetadata.playlistCount : dataset.playlists.length;
      metadataElements.playlistTotal.textContent = String(runCount);
    }
    if (metadataElements.missingCount) {
      const missing = Array.isArray(runMetadata.missingArtists) ? runMetadata.missingArtists.length : 0;
      metadataElements.missingCount.textContent = String(missing);
    }

    const tracksWithAudio = allTracks.filter((track) => {
      if (!track?.features) return false;
      return Object.values(track.features).some((value) => typeof value === "number" && value > 0);
    }).length;
    const coverage = allTracks.length ? Math.round((tracksWithAudio / allTracks.length) * 100) : 0;

    if (metadataElements.audioStatus) {
      if (coverage === 0) {
        metadataElements.audioStatus.textContent = "Audio features unavailable (API returned 403)";
        metadataElements.audioStatus.classList.add("is-warning");
        metadataElements.audioStatus.classList.remove("is-success");
      } else {
        metadataElements.audioStatus.textContent = `${coverage}% audio feature coverage`;
        metadataElements.audioStatus.classList.add("is-success");
        metadataElements.audioStatus.classList.remove("is-warning");
      }
    }

    if (elements.audioBanner) {
      if (coverage === 0) {
        elements.audioBanner.hidden = false;
      } else {
        elements.audioBanner.hidden = true;
      }
    }
  }

  function ensureCharts() {
    if (!charts.region) {
      charts.region = new Chart(elements.regionChart, {
        type: "bar",
        data: {
          labels: [],
          datasets: [
            {
              label: "Tracks",
              data: [],
              backgroundColor: "rgba(255, 180, 0, 0.75)",
              borderRadius: 8
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { ticks: { color: "#f7f8fa" }, grid: { color: "rgba(255,255,255,0.06)" } },
            y: { ticks: { color: "#f7f8fa" }, grid: { color: "rgba(255,255,255,0.06)" } }
          },
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: (context) => `${context.parsed.y} tracks`
              }
            }
          }
        }
      });
    }

    if (!charts.audio) {
      charts.audio = new Chart(elements.audioChart, {
        type: "radar",
        data: {
          labels: ["Danceability", "Energy", "Valence", "Tempo (scaled)", "Acousticness"],
          datasets: [
            {
              label: "Average",
              data: [0, 0, 0, 0, 0],
              backgroundColor: "rgba(255, 180, 0, 0.2)",
              borderColor: "rgba(255, 180, 0, 0.9)",
              pointBackgroundColor: "#ffb400"
            }
          ]
        },
        options: {
          scales: {
            r: {
              beginAtZero: true,
              max: 1,
              ticks: { display: false },
              grid: { color: "rgba(255, 255, 255, 0.12)" },
              angleLines: { color: "rgba(255, 255, 255, 0.12)" },
              pointLabels: { color: "#f7f8fa", font: { size: 12 } }
            }
          },
          plugins: {
            legend: { display: false }
          }
        }
      });
    }

    if (!charts.curator) {
      charts.curator = new Chart(elements.curatorChart, {
        type: "bar",
        data: {
          labels: [],
          datasets: [
            {
              label: "% of tracks featuring Nigerian artists",
              data: [],
              backgroundColor: "rgba(108, 99, 255, 0.75)",
              borderRadius: 8
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              beginAtZero: true,
              max: 100,
              ticks: { color: "#f7f8fa", callback: (value) => `${value}%` },
              grid: { color: "rgba(255,255,255,0.06)" }
            },
            x: {
              ticks: { color: "#f7f8fa", autoSkip: false },
              grid: { display: false }
            }
          },
          plugins: {
            legend: { display: false }
          }
        }
      });
    }
  }

  function updateCharts(allTracks, playlists) {
    ensureCharts();

    const regionCounts = sumCounts(allTracks, (track) => track.regionGroup);
    const regionLabels = Object.keys(regionCounts).sort();
    const regionValues = regionLabels.map((key) => regionCounts[key]);
    charts.region.data.labels = regionLabels;
    charts.region.data.datasets[0].data = regionValues;
    charts.region.update();

    const audioAverages = {
      danceability: average(allTracks.map((t) => t.features?.danceability || 0)),
      energy: average(allTracks.map((t) => t.features?.energy || 0)),
      valence: average(allTracks.map((t) => t.features?.valence || 0)),
      tempo: average(allTracks.map((t) => t.features?.tempo || 0)),
      acousticness: average(allTracks.map((t) => t.features?.acousticness || 0))
    };

    const tempoScaled = Math.min(audioAverages.tempo / 160, 1);
    charts.audio.data.datasets[0].data = [
      audioAverages.danceability,
      audioAverages.energy,
      audioAverages.valence,
      tempoScaled,
      audioAverages.acousticness
    ];
    charts.audio.update();

    const curatorGroups = playlists.reduce((acc, playlist) => {
      const key = playlist.curatorType;
      if (!acc[key]) {
        acc[key] = { nigeria: 0, total: 0 };
      }
      playlist.filteredTracks.forEach((track) => {
        if (track.artistCountry === "Nigeria") acc[key].nigeria += 1;
        acc[key].total += 1;
      });
      return acc;
    }, {});

    const curatorLabels = Object.keys(curatorGroups);
    const curatorValues = curatorLabels.map((label) => {
      const group = curatorGroups[label];
      if (!group.total) return 0;
      return Math.round((group.nigeria / group.total) * 100);
    });
    charts.curator.data.labels = curatorLabels;
    charts.curator.data.datasets[0].data = curatorValues;
    charts.curator.update();
  }

  function updateCards(playlists, tracks) {
    elements.playlistCount.textContent = playlists.length;
    elements.trackCount.textContent = tracks.length;

    const nigeriaTracks = tracks.filter((track) => track.artistCountry === "Nigeria").length;
    const diasporaTracks = tracks.filter((track) => track.diaspora).length;
    elements.nigeriaShare.textContent = formatPercent(nigeriaTracks, tracks.length);
    elements.diasporaShare.textContent = formatPercent(diasporaTracks, tracks.length);

    const diversityScores = playlists.map((playlist) => new Set(playlist.filteredTracks.map((track) => track.regionGroup)).size);
    const avgDiversity = diversityScores.length ? average(diversityScores).toFixed(1) : "0";
    elements.diversityScore.textContent = avgDiversity;
  }

  function renderPlaylistTable(playlists) {
    if (!playlists.length) {
      elements.playlistTable.innerHTML = "";
      elements.emptyState.hidden = false;
      return;
    }

    elements.emptyState.hidden = true;

    const rows = playlists
      .map((playlist) => {
        const totalTracks = playlist.filteredTracks.length;
        const diasporaCount = playlist.filteredTracks.filter((track) => track.diaspora).length;
        const nigeriaCount = playlist.filteredTracks.filter((track) => track.artistCountry === "Nigeria").length;
        const uniqueRegions = new Set(playlist.filteredTracks.map((track) => track.regionGroup)).size;
        const avgEnergy = average(playlist.filteredTracks.map((track) => track.features?.energy || 0)).toFixed(2);
        const avgDanceability = average(playlist.filteredTracks.map((track) => track.features?.danceability || 0)).toFixed(2);

        return `
          <tr>
            <td>
              <div style="display:flex; flex-direction:column; gap:0.35rem;">
                <strong>${playlist.name}</strong>
                <span class="tag">Launched ${playlist.launchYear}</span>
              </div>
            </td>
            <td>${playlist.curator}</td>
            <td>${formatNumber(playlist.followerCount)}</td>
            <td>${uniqueRegions}</td>
            <td>${formatPercent(diasporaCount, totalTracks)}</td>
            <td>${formatPercent(nigeriaCount, totalTracks)}</td>
            <td>${avgEnergy}</td>
            <td>${avgDanceability}</td>
          </tr>
        `;
      })
      .join("");

    elements.playlistTable.innerHTML = rows;
  }

  function updateDashboard() {
    const filteredPlaylists = filterPlaylists();
    const filteredTracks = filteredPlaylists.flatMap((playlist) => playlist.filteredTracks.map((track) => ({ ...track })));

    if (!filteredTracks.length) {
      ensureCharts();
      charts.region.data.labels = [];
      charts.region.data.datasets[0].data = [];
      charts.region.update();

      charts.audio.data.datasets[0].data = [0, 0, 0, 0, 0];
      charts.audio.update();

      charts.curator.data.labels = [];
      charts.curator.data.datasets[0].data = [];
      charts.curator.update();

      renderPlaylistTable([]);
      updateCards(filteredPlaylists, filteredTracks);
      return;
    }

    updateCards(filteredPlaylists, filteredTracks);
    updateCharts(filteredTracks, filteredPlaylists);
    renderPlaylistTable(filteredPlaylists);
  }

  initFilters();
  attachListeners();
  initMetadata();
  updateDashboard();
})();
