# Code Citations

## License: unknown
https://github.com/mikecitt/LawResolver/tree/ba51940bf6542a37fe4806bb2c188f7127bbe06f/law-resolver-ui/.github/deploy.yaml

```
:
           - main
     jobs:
       build-and-deploy:
         runs-on: ubuntu-latest
         steps:
           - uses: actions/checkout@v2
           - name: Install Dependencies
             run: npm install
           - name: Build
             run: npm run build
           - name: Deploy to Netlify
             uses: nwtgck
```


## License: unknown
https://github.com/mikecitt/LawResolver/tree/ba51940bf6542a37fe4806bb2c188f7127bbe06f/.github/workflows/deploy-ui.yaml

```
:
       build-and-deploy:
         runs-on: ubuntu-latest
         steps:
           - uses: actions/checkout@v2
           - name: Install Dependencies
             run: npm install
           - name: Build
             run: npm run build
           - name: Deploy to Netlify
             uses: nwtgck/actions-netlify
```

