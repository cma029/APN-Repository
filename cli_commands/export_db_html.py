import click
import json
from typing import List
from computations.default_polynomials import DEFAULT_IRREDUCIBLE_POLYNOMIAL
from computations.poly_parse_utils import bitmask_to_poly_str
from cli_commands.cli_utils import polynomial_to_str
from storage_pandas import load_dataframe_for_dimension


@click.command("export-html")
@click.option("--dim", "dim_n", required=True, type=int,
              help="The dimension n for GF(2^n).")
@click.option("--file-name", default=None, type=str,
              help="Custom output HTML file name. Defaults to 'vbf_n.html'.")
def export_html_cli(dim_n, file_name):
    """
    Exports the APN database (for GF(2^n)) to a single HTML file with 500 rows per page.
    If dimension <= 9, Δ-rank and Γ-rank columns are included.
    """
    apn_dataframe = load_dataframe_for_dimension(dim_n)
    if apn_dataframe.empty:
        click.echo(f"No APNs found for field_dimension={dim_n}.")
        return

    # Δ-rank and Γ-rank columns only apply for dimensions <= 9.
    rank_columns_applicable = (dim_n <= 9)

    default_irreducible_poly_int = DEFAULT_IRREDUCIBLE_POLYNOMIAL.get(dim_n, 0)
    default_irreducible_polynomial_str = (bitmask_to_poly_str(default_irreducible_poly_int)
        if default_irreducible_poly_int else "None")

    # Use the default output filename (if not provided).
    if not file_name:
        file_name = f"vbf_{dim_n}.html"

    # Build a list of row dictionaries from the DataFrame.
    apn_entries = []
    for index_value, data_row in apn_dataframe.iterrows():
        local_identifier = index_value + 1
        dimension_value = int(data_row.get("field_n", dim_n))

        # Convert stored polynomial JSON into a univariate polynomial string.
        stored_poly_json = data_row.get("poly", "")
        univariate_poly_data = []
        try:
            univariate_poly_data = json.loads(stored_poly_json) if stored_poly_json else []
        except:
            pass

        univariate_polynomial_string = polynomial_to_str(univariate_poly_data)

        # ODDS
        odds_value = data_row.get("odds", "non-quadratic")
        if isinstance(odds_value, str) and odds_value.startswith("{"):
            try:
                parsed_odds = json.loads(odds_value)
                odds_value = str(parsed_odds)
            except:
                pass

        # ODWS
        odws_value = data_row.get("odws", "non-quadratic")
        if isinstance(odws_value, str) and odws_value.startswith("{"):
            try:
                parsed_odws = json.loads(odws_value)
                odws_value = str(parsed_odws)
            except:
                pass

        # For dimensions <= 9, Δ-rank and Γ-rank.
        if rank_columns_applicable:
            delta_rank = data_row.get("delta_rank", "")
            gamma_rank = data_row.get("gamma_rank", "")
        else:
            delta_rank = ""
            gamma_rank = ""

        citation_value = data_row.get("citation", "").strip()

        apn_entries.append({
            "id": local_identifier,
            "dimension": dimension_value,
            "univariate_polynomial": univariate_polynomial_string,
            "odds": odds_value,
            "odws": odws_value,
            "delta_rank": delta_rank,
            "gamma_rank": gamma_rank,
            "citation": citation_value,
        })

    # Generate HTML content.
    html_document_skeleton = _build_html_document(
        apn_entries,
        dim_n,
        default_irreducible_polynomial_str,
        rank_columns_applicable
    )

    # Write to file.
    with open(file_name, "w", encoding="utf-8") as file_out:
        file_out.write(html_document_skeleton)

    click.echo(
        f"Exported {len(apn_entries)} APN(s) for dimension={dim_n} to '{file_name}'."
    )


def _build_html_document(apn_entries: List[dict], field_dimension: int, 
                         default_irreducible_polynomial_str: str, rank_columns_applicable: bool) -> str:
    
    css_style_block = """
      body {
        font-family: sans-serif;
        margin: 0; padding: 0;
      }
      .header {
        padding: 1rem;
        background: #f0f0f0;
        border-bottom: 1px solid #ccc;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        table-layout: auto;
      }
      th {
        background: #eee;
        white-space: nowrap; /* nowrap for column headings */
      }
      td, th {
        border: 1px solid #ccc;
        padding: 4px;
      }
      /* nowrap for ID, Dimension, Citation and ranks if n <= 9 */
      .center-col {
        text-align: center;
        white-space: nowrap;
      }
      /* break-word for univariate polynomial, ODDS and ODWS */
      .wrap-col {
        white-space: normal;
        overflow-wrap: break-word;
      }
      .pagination-controls {
        margin: 1rem 0;
        display: flex;
        align-items: center;
        gap: 1rem;
      }
      button {
        cursor: pointer;
      }
      dialog::backdrop {
        background: rgba(0,0,0,0.2);
      }
      #citationDialog {
        padding: 1rem;
        max-width: 600px;
      }
      #citationDialog pre {
        white-space: pre-wrap;
      }
    """

    # Convert the apn_entries to JSON for the JavaScript code.
    serialized_apn_data = json.dumps(apn_entries)

    javascript_code_block = r"""
      let allData = [];
      let currentPage = 1;
      const pageSize = 500;

      function loadData(data) {
        allData = data;
        currentPage = 1;
        buildPageSelect();
        renderTable();
      }

      function buildPageSelect() {
        const numberOfPages = Math.ceil(allData.length / pageSize);
        const pageSelectElements = document.querySelectorAll(".pageSelect");
        pageSelectElements.forEach(element => {
          element.innerHTML = "";
          for (let i = 1; i <= numberOfPages; i++) {
            let optionItem = document.createElement("option");
            optionItem.value = i;
            optionItem.textContent = i;
            element.appendChild(optionItem);
          }
          element.value = currentPage;
        });
      }

      function jumpToSelectedPage(selectElement) {
        currentPage = parseInt(selectElement.value, 10) || 1;
        document.querySelectorAll(".pageSelect").forEach(sel => sel.value = currentPage);
        renderTable();
      }

      function nextPage() {
        const totalPages = Math.ceil(allData.length / pageSize);
        if (currentPage < totalPages) {
          currentPage++;
          document.querySelectorAll(".pageSelect").forEach(sel => sel.value = currentPage);
          renderTable();
        }
      }

      function prevPage() {
        if (currentPage > 1) {
          currentPage--;
          document.querySelectorAll(".pageSelect").forEach(sel => sel.value = currentPage);
          renderTable();
        }
      }

      function showCitation(fullCitation) {
        const dialogElement = document.getElementById("citationDialog");
        const preElement = document.getElementById("citationText");
        preElement.textContent = fullCitation;
        dialogElement.showModal();
      }

      function closeCitation() {
        document.getElementById("citationDialog").close();
      }

      function getCitationButtonLabel(fullCitation) {
        let trimmedCitation = fullCitation.trim();
        if (trimmedCitation.startsWith("[")) {
          let closingBracket = trimmedCitation.indexOf("]");
          if (closingBracket > 1) {
            return trimmedCitation.substring(0, closingBracket + 1);
          }
        }
        return "View Citation";
      }

      function renderTable() {
        const tableBody = document.getElementById("table-body");
        tableBody.innerHTML = "";

        const startIndex = (currentPage - 1) * pageSize;
        const endIndex = Math.min(startIndex + pageSize, allData.length);

        for (let i = startIndex; i < endIndex; i++) {
          const apnRow = allData[i];
          const trElement = document.createElement("tr");

          // ID (center-column)
          let tdID = document.createElement("td");
          tdID.className = "center-col";
          tdID.textContent = apnRow.id;
          trElement.appendChild(tdID);

          // Dimension (center-column)
          let tdDimension = document.createElement("td");
          tdDimension.className = "center-col";
          tdDimension.textContent = apnRow.dimension;
          trElement.appendChild(tdDimension);

          // Univariate Polynomial (wrap-column)
          let tdPolynomial = document.createElement("td");
          tdPolynomial.className = "wrap-col";
          tdPolynomial.textContent = apnRow.univariate_polynomial;
          trElement.appendChild(tdPolynomial);

          // ODDS (wrap-column)
          let tdODDS = document.createElement("td");
          tdODDS.className = "wrap-col";
          tdODDS.textContent = apnRow.odds;
          trElement.appendChild(tdODDS);

          // ODWS (wrap-column)
          let tdODWS = document.createElement("td");
          tdODWS.className = "wrap-col";
          tdODWS.textContent = apnRow.odws;
          trElement.appendChild(tdODWS);

          // Δ-rank and Γ-rank columns (center-column)
          if (__RANK_COLUMNS__) {
            let tdDeltaRank = document.createElement("td");
            tdDeltaRank.className = "center-col";
            tdDeltaRank.textContent = apnRow.delta_rank;
            trElement.appendChild(tdDeltaRank);

            let tdGammaRank = document.createElement("td");
            tdGammaRank.className = "center-col";
            tdGammaRank.textContent = apnRow.gamma_rank;
            trElement.appendChild(tdGammaRank);
          }

          // Citation (center-column)
          let tdCitation = document.createElement("td");
          tdCitation.className = "center-col";
          if (apnRow.citation && apnRow.citation.trim().length > 0) {
            let citationString = apnRow.citation.trim();
            let citationButton = document.createElement("button");
            citationButton.textContent = getCitationButtonLabel(citationString);
            citationButton.onclick = () => showCitation(citationString);
            tdCitation.appendChild(citationButton);
          } else {
            tdCitation.textContent = "None";
          }
          trElement.appendChild(tdCitation);

          tableBody.appendChild(trElement);
        }

        const pageInfoElement = document.getElementById("page-info");
        pageInfoElement.textContent = `Page ${currentPage} of ${Math.ceil(allData.length / pageSize)} (Total: ${allData.length})`;
      }

      document.addEventListener("DOMContentLoaded", () => {
        let initialData = __APN_DATA__;
        loadData(initialData);
      });
    """

    rank_columns_str = "true" if rank_columns_applicable else "false"
    updated_javascript = (
        javascript_code_block
        .replace("__APN_DATA__", serialized_apn_data)
        .replace("__RANK_COLUMNS__", rank_columns_str)
    )

    if rank_columns_applicable:
        # If dimension <= 9 then add rank columns.
        rank_table_headers = """<th>&#916;-rank</th> <th>&#915;-rank</th>"""
    else:
        rank_table_headers = ""

    # Combine everything into final HTML.
    html_document_skeleton = f"""<!DOCTYPE html>
      <html>
      <head>
        <meta charset="UTF-8">
        <title>APN Database for GF(2^{field_dimension})</title>
        <style>
      {css_style_block}
        </style>
      </head>
      <body>

      <div class="header">
        <h1>APN Database for GF(2^{field_dimension})</h1>
        <p>Default irreducible polynomial: <b>{default_irreducible_polynomial_str}</b></p>
      </div>

      <div class="pagination-controls">
        <button onclick="prevPage()">Prev</button>
        <select class="pageSelect" onchange="jumpToSelectedPage(this)"></select>
        <button onclick="nextPage()">Next</button>
        <span id="page-info"></span>
      </div>

      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Dimension</th>
            <th>Univariate Polynomial</th>
            <th>ODDS</th>
            <th>ODWS</th>
            {rank_table_headers}
            <th>Citation</th>
          </tr>
        </thead>
        <tbody id="table-body"></tbody>
      </table>

      <div class="pagination-controls">
        <button onclick="prevPage()">Prev</button>
        <select class="pageSelect" onchange="jumpToSelectedPage(this)"></select>
        <button onclick="nextPage()">Next</button>
        <span id="page-info"></span>
      </div>

      <dialog id="citationDialog">
        <pre id="citationText"></pre>
        <div style="margin-top: 1rem; text-align: right;">
          <button onclick="closeCitation()">Close</button>
        </div>
      </dialog>

      <script>
      {updated_javascript}
      </script>

      </body>
      </html>
    """
    return html_document_skeleton