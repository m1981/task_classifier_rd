1. Keep Tests READABLE

- Write clear, descriptive test names (e.g., "should_calculate_total_price_with_discount")
- Use meaningful variable names
- Structure tests in Given-When-Then format
- Make test intention obvious

2. Keep Tests ISOLATED

- Each test should be independent
- No dependencies between tests
- Tests should be able to run in any order
- Clean up after each test

3. Test ONE THING at a time

- One logical assertion per test
- Test single behavior/feature
- Avoid testing multiple scenarios in one test
- Keep tests focused

4. Write MAINTAINABLE tests

- Don't duplicate test code (use setup methods)
- Keep test code simple
- Update tests when requirements change
- Remove obsolete tests

5. Test BEHAVIOR, not implementation

- Focus on what, not how
- Test public interfaces
- Don't test private methods
- Write tests from user's perspective