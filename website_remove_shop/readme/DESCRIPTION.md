Install the module to hide the shop on your website. Useful when you need to
accept payments on your website but don't want to show any shop product.

- The product pages (`/shop/<product>`) answer with a regular 404 page and are
  not listed in the sitemap.
- The shop listing (`/shop`, its pages and categories) redirects to the page set
  for the website, or answers with a 404 page if none is set.

The cart, checkout and payment pages are not changed by this module.
