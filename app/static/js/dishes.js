(() => {
  const form = document.getElementById("dish-filter-form");
  const tableContainer = document.getElementById("dishes-table-container");
  if (!form || !tableContainer) {
    return;
  }

  const fetchTable = async () => {
    const formData = new FormData(form);
    const params = new URLSearchParams();
    for (const [key, value] of formData.entries()) {
      if (value) {
        params.set(key, value);
      }
    }

    const url = `/dishes/table?${params.toString()}`;
    const response = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
    if (!response.ok) {
      return;
    }
    tableContainer.innerHTML = await response.text();
    window.history.replaceState({}, "", `/dishes?${params.toString()}`);
  };

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await fetchTable();
  });

  form.querySelectorAll("input, select").forEach((field) => {
    field.addEventListener("change", fetchTable);
  });
})();
