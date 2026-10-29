import copy
import json
import unittest

from aiohttp import web
from pydantic import ValidationError

from desearch_py import (
    Company,
    CompanyCompletionReason,
    CompanyEmail,
    CompanyEmailStatus,
    CompanyEnrichRequest,
    CompanyPerson,
    CompanyRequirement,
    CompanyResultsPage,
    CompanyRole,
    CompanyScore,
    CompanySearchFilters,
    CompanySearchRequest,
    CompanyTask,
    CompanyTaskConflictError,
    CompanyTaskList,
    CompanyTaskTimeoutError,
    CompanyTaskType,
    CompanyTaskWarning,
    Desearch,
    DesearchAPIError,
    DesearchResponse,
    PeopleCriterionCheck,
    PeopleExportFormat,
    PeopleTaskConflictError,
    PeopleTaskStatus,
)

TASK_ID = "5b33f3ee-168b-4780-9c8e-63a626781872"
QUERY = "Series A fintech startups in Berlin building payment infrastructure"


def _links(task_id=TASK_ID):
    base = f"/desearch/companies/tasks/{task_id}"
    return {"self": base, "results": f"{base}/results", "export": f"{base}/export"}


def _task(status="queued", **extra):
    task = {
        "task_id": TASK_ID,
        "search_type": "company_search",
        "platform": "company",
        "status": status,
        "stage": None,
        "query": QUERY,
        "count": 25,
        "result_count": 0,
        "request": {
            "query": QUERY,
            "count": 25,
            "min_score": 60,
            "exclude": ["stripe.com"],
            "roles": ["ceo", "founder", "cto", "cfo"],
            "infer_emails": True,
            "verify_emails": True,
            "filters": {"countries": ["DE"], "require": ["email"]},
        },
        "metadata": {},
        "interpreted": None,
        "progress": {},
        "errors": [],
        "completion_reason": None,
        "coverage_limited": False,
        "warnings": [],
        "reserved_cost_usd": 2.25,
        "final_cost_usd": None,
        "refunded_usd": None,
        "created_by": {"user_id": None, "api_key_id": None, "via": "api_key"},
        "created_at": "2026-10-28T10:00:00+00:00",
        "links": _links(),
    }
    task.update(extra)
    return task


def _enrich_task(status="queued", **extra):
    values = {
        "search_type": "company_enrich",
        "platform": "company_enrich",
        "query": "acme.com, beta.io",
        "count": 2,
        "request": {
            "domains": ["acme.com", "beta.io"],
            "roles": ["ceo", "cto"],
            "infer_emails": True,
            "verify_emails": True,
        },
        "reserved_cost_usd": 0.1,
    }
    values.update(extra)
    return _task(status, **values)


def _verification(status="valid", smtp="skipped", web="skipped"):
    return {
        "status": status,
        "checks": {"syntax": True, "mx": "ok", "smtp": smtp, "web": web},
        "checked_at": "2026-10-28T10:00:00Z",
    }


# The full result of docs/company-search.md in desearch-public-api.
COMPANY = {
    "id": "company:acme.com",
    "platform": "company",
    "handle": "acme.com",
    "domain": "acme.com",
    "url": "https://acme.com/",
    "name": "Acme",
    "description": "Payment infrastructure for marketplaces.",
    "logo_url": "https://acme.com/logo.png",
    "location": {
        "country": "DE",
        "city": "Berlin",
        "address": "Torstraße 1, 10119 Berlin",
    },
    "industry": "Fintech",
    "emails": [
        {
            "value": "hello@acme.com",
            "type": "general",
            "source": "website",
            "source_url": "https://acme.com/impressum",
            "on_domain": True,
            "person": None,
            "confidence": None,
            "pattern": None,
            "verification": _verification(),
        }
    ],
    "phones": [
        {
            "value": "+493012345678",
            "type": "main",
            "source": "website",
            "source_url": "https://acme.com/impressum",
            "raw": "+49 30 1234 5678",
        }
    ],
    "socials": [
        {
            "type": "linkedin",
            "url": "https://www.linkedin.com/company/acme",
            "handle": "acme",
            "source": "website",
            "source_url": "https://acme.com/",
        }
    ],
    "pages": [
        {"type": "home", "url": "https://acme.com/"},
        {"type": "imprint", "url": "https://acme.com/impressum"},
    ],
    "people": [
        {
            "name": "Anna Schmidt",
            "title": "Co-founder & CEO",
            "roles": ["ceo", "founder"],
            "linkedin_url": "https://www.linkedin.com/in/annaschmidt",
            "x_url": None,
            "github_url": None,
            "emails": [
                {
                    "value": "anna.schmidt@acme.com",
                    "type": "personal",
                    "source": "inferred",
                    "source_url": None,
                    "on_domain": True,
                    "person": "Anna Schmidt",
                    "confidence": "high",
                    "pattern": "first.last",
                    "verification": _verification(smtp="accepted", web="not_found"),
                }
            ],
            "phones": [],
            "evidence": {
                "quote": "Anna Schmidt, Geschäftsführerin",
                "source_url": "https://acme.com/impressum",
                "source": "website",
            },
            "verified": True,
        }
    ],
    "primary_email": {
        "value": "anna.schmidt@acme.com",
        "type": "personal",
        "source": "inferred",
        "source_url": None,
        "on_domain": True,
        "person": "Anna Schmidt",
        "confidence": "high",
        "pattern": "first.last",
        "verification": _verification(smtp="accepted", web="not_found"),
    },
    "primary_contact": {
        "name": "Anna Schmidt",
        "title": "Co-founder & CEO",
        "email": "anna.schmidt@acme.com",
        "linkedin_url": "https://www.linkedin.com/in/annaschmidt",
        "reason": "CEO, email inferred from the company's pattern and verified",
    },
    "contact_coverage": {
        "email": True,
        "phone": True,
        "linkedin": True,
        "leader": True,
        "leader_email": True,
    },
    "enrichment": {
        "status": "complete",
        "stages": {
            "profile": "done",
            "contacts": "done",
            "people": "done",
            "email_patterns": "done",
            "email_check": "done",
        },
        "errors": [],
    },
    "score": {
        "value": 86,
        "qualified": True,
        "relevance": "high",
        "summary": "Berlin payments infrastructure startup, Series A in 2025.",
        "matched_signals": ["payment infrastructure"],
        "reasons": ["Builds payment APIs for marketplaces"],
        "concerns": ["Series A not confirmed on the site"],
        "criteria_checks": [
            {
                "criterion": "Builds payment infrastructure",
                "verdict": "met",
                "quote": "Payment infrastructure for marketplaces.",
                "source_url": "https://acme.com/",
                "reason": "The homepage says so.",
                "is_disqualifier": False,
            },
            {
                "criterion": "Raised a Series A",
                "verdict": "unknown",
                "quote": None,
                "source_url": None,
                "reason": "No page mentions funding.",
                "is_disqualifier": False,
            },
        ],
        "fully_verified": False,
    },
    "found_by": [
        {
            "query": "fintech payment infrastructure startup Berlin",
            "url": "https://acme.com/",
            "title": "Acme — Payments",
            "kind": "direct",
        }
    ],
}


def _company(**extra):
    company = copy.deepcopy(COMPANY)
    company.update(extra)
    return company


def _enriched_company(domain="beta.io", **extra):
    """A Company Enrich result: the same fields, no score and no search."""
    company = _company(
        id=f"company:{domain}",
        handle=domain,
        domain=domain,
        url=f"https://{domain}/",
        score=None,
        found_by=[],
    )
    company.update(extra)
    return company


def _partial_company(domain="gamma.de"):
    """A company published after `profile`, before the later stages ran."""
    return {
        "id": f"company:{domain}",
        "platform": "company",
        "handle": domain,
        "domain": domain,
        "url": f"https://{domain}/",
        "name": "Gamma",
        "emails": [
            {
                "value": f"info@{domain}",
                "type": "general",
                "source": "website",
                "source_url": f"https://{domain}/",
                "on_domain": True,
                "verification": None,
            }
        ],
        "enrichment": {
            "status": "partial",
            "stages": {
                "profile": "done",
                "contacts": "pending",
                "people": "pending",
                "email_patterns": "pending",
                "email_check": "pending",
            },
            "errors": [],
        },
        "score": {"value": 71, "qualified": True, "relevance": "medium"},
    }


def _page(results, cursor="1", has_more=False, status="running"):
    return {
        "task_id": TASK_ID,
        "status": status,
        "results": results,
        "next_cursor": cursor,
        "has_more": has_more,
    }


class FakeResponse:
    def __init__(
        self, *, json_data=None, text_data="", headers=None, status=None, reason=""
    ):
        self._json_data = json_data
        self._text_data = text_data
        self.headers = headers or {}
        if status is not None:
            self.status = status
            self.reason = reason

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        return None

    async def json(self):
        return self._json_data

    async def text(self):
        if self._text_data == "" and self._json_data is not None:
            return json.dumps(self._json_data)
        return self._text_data


class FakeSession:
    closed = False

    def __init__(self, responses):
        self._responses = list(responses)
        self.requests = []

    def request(self, method, url, **kwargs):
        self.requests.append((method, url, kwargs))
        return self._responses.pop(0)

    async def close(self):
        self.closed = True


class _ClientTestCase(unittest.IsolatedAsyncioTestCase):
    def make_client(self, *responses):
        client = Desearch(api_key="test-key", base_url="https://example.test")
        client.client = FakeSession(responses)
        return client


class CompanyTaskCreateTests(_ClientTestCase):
    async def test_company_search_posts_its_route_and_returns_a_task(self):
        client = self.make_client(FakeResponse(json_data=_task(), status=202))
        task = await client.company_search(query=QUERY)
        self.assertIsInstance(task, CompanyTask)
        self.assertEqual(task.task_id, TASK_ID)
        self.assertEqual(task.search_type, "company_search")
        self.assertEqual(task.platform, "company")
        self.assertEqual(task.status, PeopleTaskStatus.QUEUED)
        self.assertFalse(task.is_finished)
        self.assertEqual(task.request["filters"]["require"], ["email"])
        self.assertEqual(
            task.links.results, f"/desearch/companies/tasks/{TASK_ID}/results"
        )
        method, url, kwargs = client.client.requests[0]
        self.assertEqual(
            (method, url), ("POST", "https://example.test/desearch/companies/search")
        )
        self.assertEqual(kwargs["json"], {"query": QUERY})
        self.assertNotIn("headers", kwargs)

    async def test_search_body_sends_every_given_field(self):
        client = self.make_client(FakeResponse(json_data=_task()))
        await client.company_search(
            query=QUERY,
            count=25,
            min_score=60,
            exclude=["stripe.com", "https://www.adyen.com/"],
            roles=[CompanyRole.CEO, "founder", CompanyRole.MANAGING_DIRECTOR],
            infer_emails=False,
            verify_emails=True,
            filters=CompanySearchFilters(
                countries=["DE"],
                require=[CompanyRequirement.EMAIL, "leader_email"],
            ),
            metadata={"campaign": "q4"},
        )
        self.assertEqual(
            client.client.requests[0][2]["json"],
            {
                "query": QUERY,
                "count": 25,
                "min_score": 60,
                "exclude": ["stripe.com", "https://www.adyen.com/"],
                "roles": ["ceo", "founder", "managing_director"],
                "infer_emails": False,
                "verify_emails": True,
                "filters": {"countries": ["DE"], "require": ["email", "leader_email"]},
                "metadata": {"campaign": "q4"},
            },
        )

    async def test_search_filters_accept_a_dict(self):
        client = self.make_client(FakeResponse(json_data=_task()))
        await client.company_search(
            query=QUERY, filters={"require": [CompanyRequirement.PHONE]}
        )
        self.assertEqual(
            client.client.requests[0][2]["json"]["filters"], {"require": ["phone"]}
        )

    async def test_bad_filters_are_rejected_before_sending(self):
        client = self.make_client()
        with self.assertRaises(ValidationError):
            await client.company_search(query=QUERY, filters={"countries": "DE"})
        self.assertEqual(client.client.requests, [])

    async def test_company_enrich_posts_domains_and_returns_an_enrich_task(self):
        client = self.make_client(FakeResponse(json_data=_enrich_task(), status=202))
        task = await client.company_enrich(
            domains=["acme.com", "https://www.beta.io/about", "Acme.com"],
            roles=[CompanyRole.CEO, CompanyRole.CTO],
            infer_emails=True,
            verify_emails=False,
        )
        self.assertIsInstance(task, CompanyTask)
        self.assertEqual(task.search_type, "company_enrich")
        self.assertEqual(task.platform, "company_enrich")
        # The API normalizes and dedupes; count is the number left.
        self.assertEqual(task.count, 2)
        self.assertEqual(task.query, "acme.com, beta.io")
        self.assertEqual(task.request["domains"], ["acme.com", "beta.io"])
        method, url, kwargs = client.client.requests[0]
        self.assertEqual(
            (method, url), ("POST", "https://example.test/desearch/companies/enrich")
        )
        self.assertEqual(
            kwargs["json"],
            {
                "domains": ["acme.com", "https://www.beta.io/about", "Acme.com"],
                "roles": ["ceo", "cto"],
                "infer_emails": True,
                "verify_emails": False,
            },
        )

    async def test_enrich_sends_only_the_domains_by_default(self):
        client = self.make_client(FakeResponse(json_data=_enrich_task()))
        await client.company_enrich(["acme.com"])
        self.assertEqual(
            client.client.requests[0][2]["json"], {"domains": ["acme.com"]}
        )

    async def test_metadata_is_sent_by_both_and_returned_on_the_task(self):
        metadata = {"workspace_id": "ws_42", "campaign": "q4"}
        for method_name, args, route, task in (
            ("company_search", {"query": QUERY}, "search", _task),
            ("company_enrich", {"domains": ["acme.com"]}, "enrich", _enrich_task),
        ):
            with self.subTest(method=method_name):
                client = self.make_client(
                    FakeResponse(json_data=task(metadata=metadata))
                )
                created = await getattr(client, method_name)(
                    **args, metadata=metadata
                )
                self.assertEqual(created.metadata, metadata)
                method, url, kwargs = client.client.requests[0]
                self.assertEqual(
                    url, f"https://example.test/desearch/companies/{route}"
                )
                self.assertEqual(kwargs["json"], {**args, "metadata": metadata})

    async def test_task_metadata_defaults_to_an_empty_dict(self):
        task = _task()
        del task["metadata"]
        client = self.make_client(FakeResponse(json_data=task))
        created = await client.company_search(query=QUERY)
        self.assertEqual(created.metadata, {})
        self.assertNotIn("metadata", client.client.requests[0][2]["json"])

    async def test_idempotency_key_is_sent_as_a_header(self):
        for method_name, args in (
            ("company_search", {"query": QUERY}),
            ("company_enrich", {"domains": ["acme.com"]}),
        ):
            with self.subTest(method=method_name):
                # A replayed key answers 200 with the earlier task.
                client = self.make_client(FakeResponse(json_data=_task(), status=200))
                task = await getattr(client, method_name)(
                    **args, idempotency_key="run-42"
                )
                self.assertEqual(task.task_id, TASK_ID)
                self.assertEqual(
                    client.client.requests[0][2]["headers"],
                    {"Idempotency-Key": "run-42"},
                )

    async def test_include_metadata_returns_the_reservation_cost(self):
        headers = {
            "X-Desearch-Cost-Usd": "2.25",
            "X-Desearch-Usage-Count": "25",
            "X-Desearch-Currency": "USD",
        }
        client = self.make_client(
            FakeResponse(
                json_data=_task(cost_usd=2.25, usage_count=25),
                headers=headers,
                status=202,
            )
        )
        response = await client.company_search(query=QUERY, include_metadata=True)
        self.assertIsInstance(response, DesearchResponse)
        self.assertIsInstance(response.data, CompanyTask)
        self.assertEqual(response.data.cost_usd, 2.25)
        self.assertEqual(response.data.usage_count, 25)
        self.assertEqual(response.metadata.cost_usd, 2.25)
        self.assertEqual(response.metadata.usage_count, 25)

    async def test_create_errors_raise_desearch_api_error(self):
        client = self.make_client(
            FakeResponse(
                json_data={"detail": "Company Enrich needs account credits."},
                status=402,
                reason="Payment Required",
            )
        )
        with self.assertRaises(DesearchAPIError) as caught:
            await client.company_enrich(["acme.com"])
        self.assertNotIsInstance(caught.exception, CompanyTaskConflictError)
        self.assertEqual(caught.exception.status, 402)
        self.assertIn("account credits", caught.exception.body)
        self.assertIsNone(caught.exception.__context__)

    def test_request_models_keep_enum_values_and_require_their_input(self):
        request = CompanySearchRequest(
            query=QUERY, roles=[CompanyRole.CFO], filters={"require": ["leader"]}
        )
        self.assertEqual(
            request.model_dump(exclude_none=True, mode="json"),
            {"query": QUERY, "roles": ["cfo"], "filters": {"require": ["leader"]}},
        )
        with self.assertRaises(ValidationError):
            CompanySearchRequest(count=5)
        with self.assertRaises(ValidationError):
            CompanyEnrichRequest(roles=["ceo"])


class CompanyTaskRouteTests(_ClientTestCase):
    async def test_list_tasks_sends_type_and_joined_statuses(self):
        client = self.make_client(
            FakeResponse(
                json_data={"tasks": [_enrich_task("running")], "next_cursor": "abc"}
            )
        )
        page = await client.list_company_tasks(
            type=CompanyTaskType.ENRICH,
            status=[PeopleTaskStatus.RUNNING, "paused"],
            limit=10,
            cursor="prev",
        )
        self.assertIsInstance(page, CompanyTaskList)
        self.assertIsInstance(page.tasks[0], CompanyTask)
        self.assertEqual(page.tasks[0].search_type, "company_enrich")
        self.assertEqual(page.next_cursor, "abc")
        method, url, kwargs = client.client.requests[0]
        self.assertEqual(
            (method, url), ("GET", "https://example.test/desearch/companies/tasks")
        )
        self.assertEqual(
            kwargs["params"],
            {"type": "enrich", "status": "running,paused", "limit": 10, "cursor": "prev"},
        )

    async def test_list_tasks_takes_plain_strings_and_no_arguments(self):
        client = self.make_client(
            FakeResponse(json_data={"tasks": [], "next_cursor": None}),
            FakeResponse(json_data={"tasks": [], "next_cursor": None}),
        )
        page = await client.list_company_tasks(type="search", status="completed")
        self.assertEqual(page.tasks, [])
        self.assertIsNone(page.next_cursor)
        await client.list_company_tasks()
        self.assertEqual(
            [kwargs["params"] for _, _, kwargs in client.client.requests],
            [{"type": "search", "status": "completed"}, {}],
        )

    async def test_list_tasks_sends_metadata_as_dotted_params(self):
        client = self.make_client(
            FakeResponse(
                json_data={
                    "tasks": [_task("completed", metadata={"campaign": "q4"})],
                    "next_cursor": None,
                }
            )
        )
        page = await client.list_company_tasks(
            type="search",
            limit=5,
            metadata={"campaign": "q4", "workspace_id": "ws_42"},
        )
        self.assertEqual(page.tasks[0].metadata, {"campaign": "q4"})
        self.assertEqual(
            client.client.requests[0][2]["params"],
            {
                "type": "search",
                "limit": 5,
                "metadata.campaign": "q4",
                "metadata.workspace_id": "ws_42",
            },
        )

    async def test_unknown_type_raises_desearch_api_error(self):
        client = self.make_client(
            FakeResponse(
                json_data={"detail": "type must be search or enrich"},
                status=400,
                reason="Bad Request",
            )
        )
        with self.assertRaises(DesearchAPIError) as caught:
            await client.list_company_tasks(type="people")
        self.assertEqual(caught.exception.status, 400)
        self.assertIn("search or enrich", caught.exception.body)

    async def test_get_task_says_why_it_ended(self):
        progress = {
            "candidates_found": 140,
            "candidates_processed": 60,
            "qualified": 25,
            "filtered": {"unreachable": 4, "not_a_company": 9, "no_email": 5},
            "enrichment": {"published": 25, "complete": 25, "pending": 0, "failed": 0},
            "email_checks": {"checked": 61, "valid": 30, "invalid": 6, "risky": 9, "unknown": 16},
            "stop_reason": "domains_done",
        }
        client = self.make_client(
            FakeResponse(
                json_data=_enrich_task(
                    "completed",
                    result_count=2,
                    progress=progress,
                    completion_reason="all_domains_processed",
                    warnings=[{"code": "linkedin_verification_unavailable", "message": "Leaders found through LinkedIn search could not be checked against their LinkedIn profiles."}],
                    final_cost_usd=0.1,
                    refunded_usd=0.0,
                    finished_at="2026-10-28T10:05:00+00:00",
                    results_expire_at="2026-11-27T10:05:00+00:00",
                )
            )
        )
        task = await client.get_company_task(TASK_ID)
        self.assertTrue(task.is_finished)
        self.assertEqual(
            task.completion_reason, CompanyCompletionReason.ALL_DOMAINS_PROCESSED
        )
        self.assertFalse(task.coverage_limited)
        self.assertIsInstance(task.warnings[0], CompanyTaskWarning)
        self.assertEqual(task.warnings[0].code, "linkedin_verification_unavailable")
        self.assertEqual(task.progress["email_checks"]["risky"], 9)
        self.assertEqual(task.final_cost_usd, 0.1)
        self.assertEqual(task.created_by.via, "api_key")
        self.assertEqual(
            client.client.requests[0][0:2],
            ("GET", f"https://example.test/desearch/companies/tasks/{TASK_ID}"),
        )

    async def test_a_task_enriching_published_companies_is_still_running(self):
        task = _task("running", stage="enriching", result_count=25)
        for key in ("completion_reason", "coverage_limited", "warnings", "request"):
            del task[key]
        client = self.make_client(FakeResponse(json_data=task))
        task = await client.get_company_task(TASK_ID)
        self.assertEqual(task.stage, "enriching")
        self.assertFalse(task.is_finished)
        self.assertIsNone(task.completion_reason)
        self.assertFalse(task.coverage_limited)
        self.assertEqual(task.warnings, [])
        self.assertIsNone(task.request)

    async def test_task_id_is_quoted_into_the_path(self):
        client = self.make_client(FakeResponse(json_data=_task()))
        await client.get_company_task("../billing?x=1")
        self.assertEqual(
            client.client.requests[0][1],
            "https://example.test/desearch/companies/tasks/..%2Fbilling%3Fx%3D1",
        )

    async def test_get_results_parses_a_full_company(self):
        client = self.make_client(
            FakeResponse(json_data=_page([_company()], cursor="1", status="completed"))
        )
        page = await client.get_company_results(TASK_ID, cursor="0", limit=50)
        self.assertIsInstance(page, CompanyResultsPage)
        self.assertEqual(page.next_cursor, "1")
        self.assertFalse(page.has_more)
        method, url, kwargs = client.client.requests[0]
        self.assertEqual(
            (method, url),
            ("GET", f"https://example.test/desearch/companies/tasks/{TASK_ID}/results"),
        )
        self.assertEqual(kwargs["params"], {"cursor": "0", "limit": 50})

        company = page.results[0]
        self.assertIsInstance(company, Company)
        self.assertEqual(
            (company.id, company.platform, company.handle, company.domain),
            ("company:acme.com", "company", "acme.com", "acme.com"),
        )
        self.assertEqual(company.location.city, "Berlin")
        self.assertEqual(company.industry, "Fintech")

        email = company.emails[0]
        self.assertIsInstance(email, CompanyEmail)
        self.assertEqual((email.value, email.type, email.source), ("hello@acme.com", "general", "website"))
        self.assertEqual(email.source_url, "https://acme.com/impressum")
        self.assertTrue(email.on_domain)
        self.assertEqual(email.verification.status, CompanyEmailStatus.VALID)
        self.assertEqual(email.verification.checks.mx, "ok")
        self.assertIs(email.verification.checks.syntax, True)

        self.assertEqual(company.phones[0].value, "+493012345678")
        self.assertEqual(company.phones[0].raw, "+49 30 1234 5678")
        self.assertEqual(company.socials[0].type, "linkedin")
        self.assertEqual(company.socials[0].handle, "acme")
        self.assertEqual([p.type for p in company.pages], ["home", "imprint"])

        leader = company.people[0]
        self.assertIsInstance(leader, CompanyPerson)
        self.assertEqual(leader.roles, ["ceo", "founder"])
        self.assertTrue(leader.verified)
        self.assertEqual(leader.evidence.quote, "Anna Schmidt, Geschäftsführerin")
        self.assertEqual(leader.phones, [])
        inferred = leader.emails[0]
        self.assertEqual(inferred.source, "inferred")
        self.assertIsNone(inferred.source_url)
        self.assertEqual((inferred.confidence, inferred.pattern), ("high", "first.last"))
        self.assertEqual(inferred.verification.checks.smtp, "accepted")
        self.assertEqual(inferred.verification.checks.web, "not_found")

        self.assertEqual(company.primary_email.value, "anna.schmidt@acme.com")
        self.assertEqual(company.primary_contact.email, "anna.schmidt@acme.com")
        self.assertTrue(company.contact_coverage.leader_email)
        self.assertEqual(company.enrichment.status, "complete")
        self.assertEqual(company.enrichment.stages.email_check, "done")
        self.assertEqual(company.enrichment.errors, [])

        score = company.score
        self.assertIsInstance(score, CompanyScore)
        self.assertEqual((score.value, score.relevance), (86, "high"))
        self.assertFalse(score.fully_verified)
        self.assertIsInstance(score.criteria_checks[0], PeopleCriterionCheck)
        self.assertFalse(score.criteria_checks[0].disqualifier)
        self.assertEqual(
            [check.criterion for check in score.unverified_criteria],
            ["Raised a Series A"],
        )
        self.assertEqual(company.found_by[0].kind, "direct")

    async def test_enrich_results_have_no_score(self):
        client = self.make_client(
            FakeResponse(
                json_data=_page([_enriched_company("beta.io")], status="completed")
            )
        )
        company = (await client.get_company_results(TASK_ID)).results[0]
        self.assertEqual(company.domain, "beta.io")
        self.assertIsNone(company.score)
        self.assertEqual(company.found_by, [])
        self.assertEqual(company.people[0].name, "Anna Schmidt")

    async def test_partial_results_parse_before_the_later_stages_ran(self):
        client = self.make_client(
            FakeResponse(json_data=_page([_partial_company()], has_more=True))
        )
        page = await client.get_company_results(TASK_ID)
        self.assertTrue(page.has_more)
        company = page.results[0]
        self.assertEqual(company.enrichment.status, "partial")
        self.assertEqual(company.enrichment.stages.profile, "done")
        self.assertEqual(company.enrichment.stages.email_check, "pending")
        self.assertIsNone(company.emails[0].verification)
        self.assertEqual(company.people, [])
        self.assertEqual(company.phones, [])
        self.assertEqual(company.socials, [])
        self.assertIsNone(company.primary_email)
        self.assertIsNone(company.primary_contact)
        self.assertIsNone(company.contact_coverage)
        self.assertIsNone(company.location)
        self.assertEqual(company.score.criteria_checks, [])
        self.assertIsNone(company.score.fully_verified)
        self.assertEqual(company.score.unverified_criteria, [])

    async def test_results_keep_fields_a_newer_api_adds(self):
        company = _company(funding={"stage": "series_a"})
        company["emails"][0]["verification"]["checks"]["dmarc"] = "ok"
        client = self.make_client(FakeResponse(json_data=_page([company])))
        parsed = (await client.get_company_results(TASK_ID)).results[0]
        self.assertEqual(parsed.funding, {"stage": "series_a"})
        self.assertEqual(parsed.emails[0].verification.checks.dmarc, "ok")

    async def test_expired_results_raise_410(self):
        client = self.make_client(
            FakeResponse(
                json_data={"detail": "Results expired 30 days after the task ended"},
                status=410,
                reason="Gone",
            )
        )
        with self.assertRaises(DesearchAPIError) as caught:
            await client.get_company_results(TASK_ID)
        self.assertEqual(caught.exception.status, 410)

    async def test_pause_resume_cancel_post_their_routes(self):
        for action, status in (
            ("pause", "pausing"),
            ("resume", "queued"),
            ("cancel", "cancelled"),
        ):
            with self.subTest(action=action):
                client = self.make_client(FakeResponse(json_data=_task(status)))
                task = await getattr(client, f"{action}_company_task")(TASK_ID)
                self.assertIsInstance(task, CompanyTask)
                self.assertEqual(task.status, status)
                self.assertEqual(
                    client.client.requests[0][0:2],
                    (
                        "POST",
                        f"https://example.test/desearch/companies/tasks/{TASK_ID}/{action}",
                    ),
                )

    async def test_conflict_raises_with_the_current_task(self):
        body = {
            "detail": "Only paused tasks can be resumed.",
            "task": _task("completed", completion_reason="count_reached"),
        }
        client = self.make_client(
            FakeResponse(json_data=body, status=409, reason="Conflict")
        )
        with self.assertRaises(CompanyTaskConflictError) as caught:
            await client.resume_company_task(TASK_ID)
        error = caught.exception
        self.assertIsInstance(error, DesearchAPIError)
        self.assertNotIsInstance(error, PeopleTaskConflictError)
        self.assertEqual(error.status, 409)
        self.assertEqual(error.message, "Conflict")
        self.assertEqual(error.detail, "Only paused tasks can be resumed.")
        self.assertIsInstance(error.task, CompanyTask)
        self.assertEqual(error.task.status, "completed")
        self.assertEqual(error.task.completion_reason, "count_reached")
        self.assertIsNone(error.__cause__)
        self.assertIsNone(error.__context__)
        self.assertIn("409", str(error))

    async def test_conflict_with_an_unreadable_body_keeps_task_none(self):
        client = self.make_client(
            FakeResponse(text_data="not json", status=409, reason="Conflict")
        )
        with self.assertRaises(CompanyTaskConflictError) as caught:
            await client.cancel_company_task(TASK_ID)
        self.assertIsNone(caught.exception.task)
        self.assertEqual(caught.exception.detail, "")
        self.assertEqual(caught.exception.body, "not json")

    async def test_a_people_search_task_is_a_404_here(self):
        client = self.make_client(
            FakeResponse(
                json_data={"detail": "Task not found"}, status=404, reason="Not Found"
            )
        )
        with self.assertRaises(DesearchAPIError) as caught:
            await client.pause_company_task(TASK_ID)
        self.assertNotIsInstance(caught.exception, CompanyTaskConflictError)
        self.assertEqual(caught.exception.status, 404)

    def test_enums_match_the_api_values(self):
        self.assertEqual([t.value for t in CompanyTaskType], ["search", "enrich"])
        self.assertEqual(
            [role.value for role in CompanyRole],
            [
                "ceo",
                "founder",
                "cto",
                "cfo",
                "coo",
                "cmo",
                "president",
                "owner",
                "managing_director",
            ],
        )
        self.assertEqual(
            [r.value for r in CompanyRequirement],
            ["email", "phone", "linkedin", "leader", "leader_email"],
        )
        self.assertEqual(
            [reason.value for reason in CompanyCompletionReason],
            [
                "count_reached",
                "all_domains_processed",
                "rounds_exhausted",
                "no_candidates",
                "zero_qualified",
                "candidate_budget",
                "cost_limit",
                "time_limit",
                "cancelled",
                "failed",
            ],
        )
        self.assertEqual(
            [s.value for s in CompanyEmailStatus],
            ["valid", "invalid", "risky", "unknown"],
        )


class CompanyExportTests(_ClientTestCase):
    async def test_export_defaults_to_csv(self):
        csv_text = "domain,name,url\nacme.com,Acme,https://acme.com/\n"
        client = self.make_client(FakeResponse(text_data=csv_text))
        self.assertEqual(await client.export_company_results(TASK_ID), csv_text)
        method, url, kwargs = client.client.requests[0]
        self.assertEqual(
            (method, url),
            ("GET", f"https://example.test/desearch/companies/tasks/{TASK_ID}/export"),
        )
        self.assertEqual(kwargs["params"], {"format": "csv"})

    async def test_export_jsonl_with_metadata(self):
        line = json.dumps(_partial_company()) + "\n"
        client = self.make_client(
            FakeResponse(text_data=line, headers={"X-Desearch-Cost-Usd": "0"})
        )
        response = await client.export_company_results(
            TASK_ID, format=PeopleExportFormat.JSONL, include_metadata=True
        )
        self.assertIsInstance(response, DesearchResponse)
        self.assertEqual(response.metadata.cost_usd, 0.0)
        self.assertEqual(client.client.requests[0][2]["params"], {"format": "jsonl"})
        company = Company(**json.loads(response.data))
        self.assertEqual(company.enrichment.status, "partial")


class CompanyHelperTests(_ClientTestCase):
    async def test_wait_polls_until_the_task_ends(self):
        client = self.make_client(
            FakeResponse(json_data=_task("queued")),
            FakeResponse(json_data=_task("running", stage="enriching", result_count=25)),
            FakeResponse(json_data=_task("completed", result_count=25)),
        )
        task = await client.wait_for_company_task(TASK_ID, poll_interval=0)
        self.assertIsInstance(task, CompanyTask)
        self.assertEqual(task.status, "completed")
        self.assertEqual(task.result_count, 25)
        self.assertEqual(len(client.client.requests), 3)
        for method, url, _ in client.client.requests:
            self.assertEqual(
                (method, url),
                ("GET", f"https://example.test/desearch/companies/tasks/{TASK_ID}"),
            )

    async def test_wait_returns_at_once_for_an_ended_task(self):
        client = self.make_client(FakeResponse(json_data=_task("cancelled")))
        task = await client.wait_for_company_task(TASK_ID, timeout=0)
        self.assertEqual(task.status, "cancelled")
        self.assertEqual(len(client.client.requests), 1)

    async def test_wait_raises_on_timeout_with_the_last_task(self):
        for task, product in (
            (_task("paused"), "Company Search"),
            (_enrich_task("running", stage="enriching"), "Company Enrich"),
        ):
            with self.subTest(product=product):
                client = self.make_client(FakeResponse(json_data=task))
                with self.assertRaises(CompanyTaskTimeoutError) as caught:
                    await client.wait_for_company_task(
                        TASK_ID, poll_interval=0, timeout=0
                    )
                self.assertIsInstance(caught.exception, TimeoutError)
                self.assertEqual(caught.exception.task.status, task["status"])
                self.assertIn(TASK_ID, str(caught.exception))
                self.assertTrue(str(caught.exception).startswith(product))
                self.assertEqual(len(client.client.requests), 1)

    async def test_iter_results_follows_cursors(self):
        client = self.make_client(
            FakeResponse(
                json_data=_page(
                    [_company(), _partial_company("b.io")], cursor="2", has_more=True
                )
            ),
            FakeResponse(json_data=_page([_partial_company("c.io")], cursor="3")),
        )
        domains = [
            company.domain
            async for company in client.iter_company_results(TASK_ID, page_size=2)
        ]
        self.assertEqual(domains, ["acme.com", "b.io", "c.io"])
        self.assertEqual(
            [kwargs["params"] for _, _, kwargs in client.client.requests],
            [{"limit": 2}, {"cursor": "2", "limit": 2}],
        )

    async def test_iter_results_stops_on_an_empty_page(self):
        client = self.make_client(
            FakeResponse(json_data=_page([], cursor="5", has_more=True))
        )
        companies = [
            company
            async for company in client.iter_company_results(TASK_ID, cursor="5")
        ]
        self.assertEqual(companies, [])
        self.assertEqual(
            client.client.requests[0][2]["params"], {"cursor": "5", "limit": 100}
        )


KEY = "fake-key-for-company-tests"


class CompanySearchHttpTests(unittest.IsolatedAsyncioTestCase):
    """Runs the client against a local aiohttp server to check real requests."""

    async def asyncSetUp(self):
        self.seen = []

        async def handler(request):
            self.seen.append(
                {
                    "method": request.method,
                    "path": request.path,
                    "query": request.query_string,
                    "params": list(request.query.items()),
                    "authorization": request.headers.get("Authorization"),
                    "idempotency_key": request.headers.get("Idempotency-Key"),
                    "body": await request.text(),
                }
            )
            path = request.path
            if path.endswith("/export"):
                return web.Response(
                    text="domain,name\nacme.com,Acme\n", content_type="text/csv"
                )
            if path.endswith("/pause"):
                body = {
                    "detail": "Only queued or running tasks can be paused. " + KEY,
                    "task": _task("completed"),
                }
                return web.json_response(body, status=409)
            if path.endswith("/results"):
                return web.json_response(_page([_company()], status="completed"))
            if path == "/desearch/companies/search":
                return web.json_response(_task(), status=202)
            if path == "/desearch/companies/enrich":
                return web.json_response(_enrich_task(), status=202)
            return web.json_response({"tasks": [], "next_cursor": None})

        app = web.Application()
        app.router.add_route("*", "/{tail:.*}", handler)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, "127.0.0.1", 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        self.client = Desearch(api_key=KEY, base_url=f"http://127.0.0.1:{port}")

    async def asyncTearDown(self):
        await self.client.close()
        await self.runner.cleanup()

    async def test_create_calls_send_body_auth_and_idempotency_key(self):
        task = await self.client.company_search(
            query=QUERY,
            count=10,
            roles=[CompanyRole.CEO],
            filters={"countries": ["DE"], "require": ["email"]},
            idempotency_key="run-1",
        )
        self.assertEqual(task.search_type, "company_search")
        enrich = await self.client.company_enrich(
            ["acme.com", "beta.io"], verify_emails=False
        )
        self.assertEqual(enrich.search_type, "company_enrich")
        search, enrich_seen = self.seen
        self.assertEqual(
            (search["method"], search["path"]), ("POST", "/desearch/companies/search")
        )
        self.assertEqual(search["authorization"], KEY)
        self.assertEqual(search["idempotency_key"], "run-1")
        self.assertEqual(
            json.loads(search["body"]),
            {
                "query": QUERY,
                "count": 10,
                "roles": ["ceo"],
                "filters": {"countries": ["DE"], "require": ["email"]},
            },
        )
        self.assertEqual(enrich_seen["path"], "/desearch/companies/enrich")
        self.assertIsNone(enrich_seen["idempotency_key"])
        self.assertEqual(
            json.loads(enrich_seen["body"]),
            {"domains": ["acme.com", "beta.io"], "verify_emails": False},
        )

    async def test_task_filters_and_export_reach_the_server_as_query_params(self):
        page = await self.client.list_company_tasks(
            type=CompanyTaskType.SEARCH,
            status=["running", "paused"],
            metadata={"campaign": "q4 outbound & more", "team.id": "t-1"},
        )
        self.assertEqual(page.tasks, [])
        csv_text = await self.client.export_company_results(TASK_ID, format="jsonl")
        self.assertIn("acme.com", csv_text)
        companies = [c async for c in self.client.iter_company_results(TASK_ID)]
        self.assertEqual(companies[0].people[0].emails[0].confidence, "high")
        self.assertEqual(self.seen[0]["path"], "/desearch/companies/tasks")
        self.assertEqual(
            self.seen[0]["params"],
            [
                ("type", "search"),
                ("status", "running,paused"),
                ("metadata.campaign", "q4 outbound & more"),
                ("metadata.team.id", "t-1"),
            ],
        )
        self.assertEqual(
            self.seen[1]["path"], f"/desearch/companies/tasks/{TASK_ID}/export"
        )
        self.assertEqual(self.seen[1]["query"], "format=jsonl")
        self.assertEqual(
            self.seen[2]["path"], f"/desearch/companies/tasks/{TASK_ID}/results"
        )
        self.assertEqual(self.seen[2]["query"], "limit=100")

    async def test_conflict_over_http_is_parsed_and_redacted(self):
        with self.assertRaises(CompanyTaskConflictError) as caught:
            await self.client.pause_company_task(TASK_ID)
        error = caught.exception
        self.assertEqual(error.status, 409)
        self.assertEqual(error.task.status, "completed")
        self.assertEqual(
            error.detail, "Only queued or running tasks can be paused. [REDACTED]"
        )
        self.assertNotIn(KEY, error.body)
        self.assertNotIn(KEY, repr(error))
        self.assertIsNone(error.__context__)


if __name__ == "__main__":
    unittest.main()
