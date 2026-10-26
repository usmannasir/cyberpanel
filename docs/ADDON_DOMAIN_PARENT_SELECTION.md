# Addon domain parent selection

The Create Sub/Addon Domain form requires a Parent Website for both domain types.
Switching between Sub Domain and Addon Domain preserves that selection; it does
not replace it with the account's default website. Clearing the parent hides the
remaining creation form and prevents a creation request.

The existing backend ownership check remains authoritative. This change does not
move existing domains or change the fixed parent used by the domain-alias page.
Both shipped JavaScript copies contain the same bounded controller change; the
creation page's asset version invalidates the prior cached controller.

Run the focused regressions from the repository root:

```sh
node websiteFunctions/test_addon_parent_selection.js
python3 -m unittest websiteFunctions.test_addon_parent_ownership websiteFunctions.test_domain_alias_template websiteFunctions.test_apache_entitlements
```

Browser acceptance: offer `alpha.example` and `zeta.example` with alpha as the
account default. Repeat with the option order reversed. Select zeta, switch from
Sub Domain to Addon Domain and back, then submit an addon. The parent selector
must remain visible, the displayed home path must remain under zeta, and the
creation POST must contain `masterDomain: zeta.example`. Clear the selection and
verify no creation POST occurs. Also verify choosing Addon Domain first requires
a parent. Use a disposable environment or intercept the POST when testing only
the form; request capture is not proof of provisioning a live domain.
