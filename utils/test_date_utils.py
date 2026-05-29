import unittest
from utils import date_utils


class TestDateUtils(unittest.TestCase):
    """Unit tests for date_utils module."""

    # =========================================================================
    # Tests for to_iso8601_utc()
    # =========================================================================

    def test_to_iso8601_utc_already_iso8601(self):
        """Test that ISO-8601 UTC dates are returned unchanged."""
        iso_date = "2026-05-19T05:28:45.000Z"
        result = date_utils.to_iso8601_utc(iso_date)
        self.assertEqual(result, iso_date)

    def test_to_iso8601_utc_from_rfc1123_gmt(self):
        """Test conversion from RFC-1123 GMT to ISO-8601 UTC."""
        rfc_date = "Tue, 19 May 2026 05:28:45 GMT"
        result = date_utils.to_iso8601_utc(rfc_date)
        self.assertEqual(result, "2026-05-19T05:28:45.000Z")

    def test_to_iso8601_utc_empty_string_returns_epoch(self):
        """Test that empty string returns epoch timestamp."""
        result = date_utils.to_iso8601_utc("")
        self.assertEqual(result, "1970-01-01T00:00:00.000Z")

    def test_to_iso8601_utc_none_returns_epoch(self):
        """Test that None returns epoch timestamp."""
        result = date_utils.to_iso8601_utc(None)
        self.assertEqual(result, "1970-01-01T00:00:00.000Z")

    def test_to_iso8601_utc_invalid_format_returns_epoch(self):
        """Test that invalid date format returns epoch timestamp."""
        result = date_utils.to_iso8601_utc("invalid-date")
        self.assertEqual(result, "1970-01-01T00:00:00.000Z")

    def test_to_iso8601_utc_rfc1123_different_day_gmt(self):
        """Test RFC-1123 GMT conversion for different day of week."""
        rfc_date = "Mon, 01 Jan 2024 12:00:00 GMT"
        result = date_utils.to_iso8601_utc(rfc_date)
        self.assertEqual(result, "2024-01-01T12:00:00.000Z")

    def test_to_iso8601_utc_rfc1123_end_of_month(self):
        """Test RFC-1123 GMT conversion for end of month."""
        rfc_date = "Fri, 31 Dec 2024 23:59:59 GMT"
        result = date_utils.to_iso8601_utc(rfc_date)
        self.assertEqual(result, "2024-12-31T23:59:59.000Z")

    # =========================================================================
    # Tests for to_rfc1123_utc()
    # =========================================================================

    def test_to_rfc1123_utc_already_rfc1123_gmt(self):
        """Test that RFC-1123 GMT UTC dates are returned unchanged."""
        rfc_date = "Tue, 19 May 2026 05:28:45 GMT"
        result = date_utils.to_rfc1123_utc(rfc_date)
        self.assertEqual(result, rfc_date)

    def test_to_rfc1123_utc_from_iso8601_with_milliseconds(self):
        """Test conversion from ISO-8601 with milliseconds to RFC-1123 GMT."""
        iso_date = "2026-05-19T05:28:45.000Z"
        result = date_utils.to_rfc1123_utc(iso_date)
        self.assertEqual(result, "Tue, 19 May 2026 05:28:45 GMT")

    def test_to_rfc1123_utc_from_iso8601_without_milliseconds(self):
        """Test conversion from ISO-8601 without milliseconds to RFC-1123 GMT."""
        iso_date = "2026-05-19T05:28:45Z"
        result = date_utils.to_rfc1123_utc(iso_date)
        self.assertEqual(result, "Tue, 19 May 2026 05:28:45 GMT")

    def test_to_rfc1123_utc_empty_string_returns_epoch(self):
        """Test that empty string returns epoch timestamp in RFC-1123 GMT."""
        result = date_utils.to_rfc1123_utc("")
        self.assertEqual(result, "Thu, 01 Jan 1970 00:00:00 GMT")

    def test_to_rfc1123_utc_none_returns_epoch(self):
        """Test that None returns epoch timestamp in RFC-1123 GMT."""
        result = date_utils.to_rfc1123_utc(None)
        self.assertEqual(result, "Thu, 01 Jan 1970 00:00:00 GMT")

    def test_to_rfc1123_utc_invalid_format_returns_epoch(self):
        """Test that invalid date format returns epoch timestamp."""
        result = date_utils.to_rfc1123_utc("invalid-date")
        self.assertEqual(result, "Thu, 01 Jan 1970 00:00:00 GMT")

    def test_to_rfc1123_utc_iso8601_different_date(self):
        """Test ISO-8601 conversion for different date to RFC-1123 GMT."""
        iso_date = "2024-12-25T18:45:30.500Z"
        result = date_utils.to_rfc1123_utc(iso_date)
        self.assertEqual(result, "Wed, 25 Dec 2024 18:45:30 GMT")

    def test_to_rfc1123_utc_iso8601_end_of_year(self):
        """Test ISO-8601 conversion for end of year to RFC-1123 GMT."""
        iso_date = "2024-12-31T23:59:59.999Z"
        result = date_utils.to_rfc1123_utc(iso_date)
        self.assertEqual(result, "Tue, 31 Dec 2024 23:59:59 GMT")

    # =========================================================================
    # Round-trip conversions (GMT only, per implementation)
    # =========================================================================

    def test_rfc1123_gmt_to_iso8601_and_back(self):
        """Test round-trip conversion from RFC-1123 GMT to ISO-8601 and back."""
        original = "Mon, 15 Jul 2024 14:30:00 GMT"
        iso = date_utils.to_iso8601_utc(original)
        result = date_utils.to_rfc1123_utc(iso)
        self.assertEqual(result, original)

    def test_iso8601_to_rfc1123_and_back(self):
        """Test round-trip conversion from ISO-8601 to RFC-1123 and back."""
        original = "2024-07-15T14:30:00.000Z"
        rfc = date_utils.to_rfc1123_utc(original)
        result = date_utils.to_iso8601_utc(rfc)
        self.assertEqual(result, original)

    def test_gmt_unchanged_through_conversions(self):
        """Test that GMT dates remain consistent through multiple cycles."""
        original_rfc = "Sat, 21 Mar 2026 12:00:00 GMT"
        iso = date_utils.to_iso8601_utc(original_rfc)
        self.assertEqual(iso, "2026-03-21T12:00:00.000Z")
        rfc1 = date_utils.to_rfc1123_utc(iso)
        self.assertEqual(rfc1, original_rfc)
        iso2 = date_utils.to_iso8601_utc(rfc1)
        self.assertEqual(iso2, iso)
        rfc2 = date_utils.to_rfc1123_utc(iso2)
        self.assertEqual(rfc2, rfc1)

    # =========================================================================
    # Edge cases
    # =========================================================================

    def test_iso8601_with_different_millisecond_precisions(self):
        """Test ISO-8601 handling with different millisecond precisions."""
        iso_500ms = "2024-07-15T12:00:00.500Z"
        result = date_utils.to_rfc1123_utc(iso_500ms)
        self.assertEqual(result, "Mon, 15 Jul 2024 12:00:00 GMT")

    def test_leap_year_date_conversion(self):
        """Test conversion of leap year date (Feb 29)."""
        rfc_date = "Thu, 29 Feb 2024 10:00:00 GMT"
        iso = date_utils.to_iso8601_utc(rfc_date)
        self.assertEqual(iso, "2024-02-29T10:00:00.000Z")
        result = date_utils.to_rfc1123_utc(iso)
        self.assertEqual(result, rfc_date)

    def test_malformed_rfc1123_returns_epoch(self):
        """Test malformed RFC-1123 date returns epoch."""
        result = date_utils.to_iso8601_utc("Mon, 32 Jan 2024 12:00:00 GMT")
        self.assertEqual(result, "1970-01-01T00:00:00.000Z")

    def test_malformed_iso8601_returns_epoch(self):
        """Test malformed ISO-8601 date returns epoch."""
        result = date_utils.to_rfc1123_utc("2024-13-01T12:00:00.000Z")
        self.assertEqual(result, "Thu, 01 Jan 1970 00:00:00 GMT")


if __name__ == "__main__":
    unittest.main()