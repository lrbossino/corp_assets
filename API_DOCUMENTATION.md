## V3 API Integration Documentation

This document outlines the API choices, limitations, and future alternatives for the real tool integrations in the V3 Corporate Asset Research Agent.

### Guiding Principles

1.  **Prioritize Free APIs**: All default integrations use APIs that are free and, where possible, do not require an API key. This ensures the application works out-of-the-box without setup costs.
2.  **Document Limitations**: Be transparent about the limitations of free APIs (rate limits, accuracy, reliability) compared to paid alternatives.
3.  **Provide Upgrade Paths**: For each tool, suggest paid alternatives that offer better performance, reliability, or features.

---

### Tool-by-Tool API Breakdown

#### 1. Web Search (`search_web`)

*   **Selected Free API**: **DuckDuckGo Search**
    *   **Library**: `duckduckgo-search`
    *   **Why**: Completely free, no API key required, no official query limits (though respectful rate limiting is advised). It's the easiest way to get programmatic web search results without any setup.
    *   **Limitations**: Results may be less comprehensive or accurate than Google/Bing. It can be blocked by firewalls or captchas if used too aggressively.
    *   **Source Confidence**: `0.7` (Credible web sources)

*   **Paid Alternatives**:
    *   **Serper.dev**: A low-cost Google Search API. Offers 2,500 free queries on signup, then is very cheap. More reliable than scraping.
    *   **SerpAPI**: A more expensive but very powerful search API that handles proxies and captchas. Provides structured JSON output for various search types.
    *   **Google Custom Search API**: The official way to use Google Search. Has a free tier (100 queries/day) but requires setup and an API key.

#### 2. Document Parsing (`parse_document`)

*   **Selected Free Libraries**:
    *   **PDFs**: `pdfplumber`
    *   **Webpages**: `requests` + `BeautifulSoup`
    *   **Why**: Both are powerful, open-source Python libraries that run locally. They require no external APIs or costs and are highly effective for extracting text and structured data.
    *   **Limitations**: Web scraping with BeautifulSoup can be brittle. If a website's HTML structure changes, the scraper may break. It also doesn't handle JavaScript-heavy sites well. `pdfplumber` is excellent for text-based PDFs but struggles with scanned/image-based documents.
    *   **Source Confidence**: `0.8` (Webpages) to `0.95` (PDFs)

*   **Paid Alternatives**:
    *   **ScrapingBee / Scrapy / Bright Data**: Managed web scraping services that handle proxies, JavaScript rendering, and captchas, making scraping far more reliable.
    *   **AWS Textract / Google Cloud Vision AI**: For scanned PDFs, these services use OCR to extract text with high accuracy.

#### 3. Registry Lookup (`lookup_registry`)

*   **Selected Free APIs**:
    *   **US SEC**: Official **SEC EDGAR API**
    *   **UK Companies House**: Official **Companies House API**
    *   **Why**: These are official government APIs. They are free, require no authentication, and provide the most accurate, authoritative data.
    *   **Limitations**: Each API only covers its specific jurisdiction. Expanding to other countries would require finding and integrating with their respective (and often non-existent) free APIs.
    *   **Source Confidence**: `1.0` (Official government data)

*   **Paid Alternatives**:
    *   **OpenCorporates**: A comprehensive database of company registry information from around the world. The definitive source for this kind of data, but it is a paid service.

#### 4. Geocoding (`get_coordinates`)

*   **Selected Free API**: **OpenStreetMap Nominatim**
    *   **Library**: `geopy`
    *   **Why**: A widely used, free, and open geocoding service. `geopy` provides a convenient wrapper, and it requires no API key.
    *   **Limitations**: Has a strict usage policy of **1 request per second**. It is also generally less accurate for specific rooftop-level addresses compared to paid services like Google Maps.
    *   **Source Confidence**: `0.85` (Verified coordinates)

*   **Paid Alternatives**:
    *   **Google Maps Geocoding API**: The industry standard. Highly accurate and reliable, with a generous free tier but becomes paid after that.
    *   **Mapbox Geocoding API**: Another excellent paid alternative known for its quality and developer-friendly tools.

#### 5. Job Postings (`search_job_postings`)

*   **Selected Free Method**: **Web Search Scraping**
    *   **Why**: There are **no official, free APIs** for major job boards like LinkedIn or Indeed. The only free method is to use a web search (via DuckDuckGo) with specific queries (e.g., `"Apple Inc. jobs" site:linkedin.com/jobs`) and scrape the results.
    *   **Limitations**: This is the most unreliable tool. It depends entirely on what the search engine indexes and is prone to being blocked. It can only provide clues (e.g., a job posting for a "Data Center Technician in Prineville, Oregon") rather than a structured list of facilities.
    *   **Source Confidence**: `0.6` (Location clues)

*   **Paid Alternatives**:
    *   **Web Scraping Services (Bright Data, etc.)**: A paid scraping service could be tasked with systematically scraping job boards for more reliable data.
    *   **LinkedIn API**: Requires a partnership or enterprise agreement and is not generally available.

### API Key Management

*   **Free APIs**: No keys are needed for the selected free APIs, so they are embedded directly.
*   **Paid APIs**: For future integrations, API keys should **NEVER** be hardcoded. They should be managed via:
    *   **Environment Variables**: The standard `dotenv` approach is implemented.
    *   **Secrets Management Services**: For production, use AWS Secrets Manager, Google Secret Manager, or HashiCorp Vault.
