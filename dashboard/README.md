# SRI Testing Dashboard

## .env configuration

The Dashboard relies on some site specific parameters - encoded in a **.env** environmental variable configuration file -to work properly.

Note that the **.env** file is **.gitignored** in the repo. A template file, [dot_env_template](dot_env_template) is provided. A copy of this file should be made into a file called **.env** and customized to site requirements (see below).

### Setting up API connection

In the `.env` file in `dashboard/`, set `API_HOST` to the domain name of the API, and `API_PORT` to the port of the API, if applicable.

The default protocol is `http://`.

## Build Setup

``` bash
# install dependencies
npm install

# serve with hot reload at localhost:8081
npm run dev

# build for production with minification
npm run build

# build for production and view the bundle analyzer report
npm run build --report

# run unit tests
npm run unit

# run e2e tests
npm run e2e

# run all tests
npm test
```

For a detailed explanation on how things work, check out the [guide](http://vuejs-templates.github.io/webpack/) and [docs for vue-loader](http://vuejs.github.io/vue-loader).
