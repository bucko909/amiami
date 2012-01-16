--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

--
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


SET search_path = public, pg_catalog;

--
-- Name: categories_id_seq; Type: SEQUENCE; Schema: public; Owner: amiami
--

CREATE SEQUENCE categories_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.categories_id_seq OWNER TO amiami;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: categories; Type: TABLE; Schema: public; Owner: amiami; Tablespace: 
--

CREATE TABLE categories (
    id integer DEFAULT nextval('categories_id_seq'::regclass) NOT NULL,
    name text NOT NULL,
    code text NOT NULL,
    var text DEFAULT 'CategoryNickname'::text NOT NULL
);


ALTER TABLE public.categories OWNER TO amiami;

--
-- Name: pages_id_seq; Type: SEQUENCE; Schema: public; Owner: amiami
--

CREATE SEQUENCE pages_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.pages_id_seq OWNER TO amiami;

--
-- Name: pages; Type: TABLE; Schema: public; Owner: amiami; Tablespace: 
--

CREATE TABLE pages (
    id integer DEFAULT nextval('pages_id_seq'::regclass) NOT NULL,
    last_update timestamp without time zone
);


ALTER TABLE public.pages OWNER TO amiami;

--
-- Name: product_categories_id_seq; Type: SEQUENCE; Schema: public; Owner: amiami
--

CREATE SEQUENCE product_categories_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.product_categories_id_seq OWNER TO amiami;

--
-- Name: product_categories; Type: TABLE; Schema: public; Owner: amiami; Tablespace: 
--

CREATE TABLE product_categories (
    id integer DEFAULT nextval('product_categories_id_seq'::regclass) NOT NULL,
    product_id integer NOT NULL,
    category_id integer NOT NULL
);


ALTER TABLE public.product_categories OWNER TO amiami;

--
-- Name: product_update_seq; Type: SEQUENCE; Schema: public; Owner: amiami
--

CREATE SEQUENCE product_update_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.product_update_seq OWNER TO amiami;

--
-- Name: product_updates_id_seq; Type: SEQUENCE; Schema: public; Owner: amiami
--

CREATE SEQUENCE product_updates_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.product_updates_id_seq OWNER TO amiami;

--
-- Name: product_updates; Type: TABLE; Schema: public; Owner: amiami; Tablespace: 
--

CREATE TABLE product_updates (
    id integer DEFAULT nextval('product_updates_id_seq'::regclass) NOT NULL,
    diff text NOT NULL,
    cr_date timestamp without time zone DEFAULT now() NOT NULL,
    product_id integer NOT NULL
);


ALTER TABLE public.product_updates OWNER TO amiami;

--
-- Name: products_id_seq; Type: SEQUENCE; Schema: public; Owner: amiami
--

CREATE SEQUENCE products_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.products_id_seq OWNER TO amiami;

--
-- Name: products; Type: TABLE; Schema: public; Owner: amiami; Tablespace: 
--

CREATE TABLE products (
    id integer DEFAULT nextval('products_id_seq'::regclass) NOT NULL,
    name text,
    url text,
    image text,
    stock text,
    status text,
    price integer,
    discount integer,
    updateseq integer NOT NULL,
    cr_date timestamp without time zone DEFAULT now() NOT NULL,
    last_info_fetch timestamp without time zone,
    last_site_update timestamp without time zone,
    code text
);


ALTER TABLE public.products OWNER TO amiami;

--
-- Name: categories_pkey; Type: CONSTRAINT; Schema: public; Owner: amiami; Tablespace: 
--

ALTER TABLE ONLY categories
    ADD CONSTRAINT categories_pkey PRIMARY KEY (id);


--
-- Name: pages_pkey; Type: CONSTRAINT; Schema: public; Owner: amiami; Tablespace: 
--

ALTER TABLE ONLY pages
    ADD CONSTRAINT pages_pkey PRIMARY KEY (id);


--
-- Name: product_categories_pkey; Type: CONSTRAINT; Schema: public; Owner: amiami; Tablespace: 
--

ALTER TABLE ONLY product_categories
    ADD CONSTRAINT product_categories_pkey PRIMARY KEY (id);


--
-- Name: product_updates_pkey; Type: CONSTRAINT; Schema: public; Owner: amiami; Tablespace: 
--

ALTER TABLE ONLY product_updates
    ADD CONSTRAINT product_updates_pkey PRIMARY KEY (id);


--
-- Name: products_pkey; Type: CONSTRAINT; Schema: public; Owner: amiami; Tablespace: 
--

ALTER TABLE ONLY products
    ADD CONSTRAINT products_pkey PRIMARY KEY (id);


--
-- Name: ip_pc; Type: INDEX; Schema: public; Owner: amiami; Tablespace: 
--

CREATE INDEX ip_pc ON product_categories USING btree (product_id);


--
-- Name: product_updates_cr_date; Type: INDEX; Schema: public; Owner: amiami; Tablespace: 
--

CREATE INDEX product_updates_cr_date ON product_updates USING btree (cr_date);


--
-- Name: products_status; Type: INDEX; Schema: public; Owner: amiami; Tablespace: 
--

CREATE INDEX products_status ON products USING btree (status);


--
-- Name: products_stock; Type: INDEX; Schema: public; Owner: amiami; Tablespace: 
--

CREATE INDEX products_stock ON products USING btree (stock);


--
-- Name: products_url; Type: INDEX; Schema: public; Owner: amiami; Tablespace: 
--

CREATE INDEX products_url ON products USING btree (url);


--
-- Name: products_url_unique; Type: INDEX; Schema: public; Owner: amiami; Tablespace: 
--

CREATE UNIQUE INDEX products_url_unique ON products USING btree (url);


--
-- Name: ucc; Type: INDEX; Schema: public; Owner: amiami; Tablespace: 
--

CREATE UNIQUE INDEX ucc ON categories USING btree (code);


--
-- Name: upc; Type: INDEX; Schema: public; Owner: amiami; Tablespace: 
--

CREATE UNIQUE INDEX upc ON product_categories USING btree (category_id, product_id);


--
-- Name: product_categories_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: amiami
--

ALTER TABLE ONLY product_categories
    ADD CONSTRAINT product_categories_category_id_fkey FOREIGN KEY (category_id) REFERENCES categories(id);


--
-- Name: product_categories_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: amiami
--

ALTER TABLE ONLY product_categories
    ADD CONSTRAINT product_categories_product_id_fkey FOREIGN KEY (product_id) REFERENCES products(id);


--
-- Name: product_updates_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: amiami
--

ALTER TABLE ONLY product_updates
    ADD CONSTRAINT product_updates_product_id_fkey FOREIGN KEY (product_id) REFERENCES products(id);


--
-- Name: public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM postgres;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- PostgreSQL database dump complete
--

